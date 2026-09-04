package main

import (
	"flag"
	"fmt"
	"go/ast"
	"go/parser"
	"go/token"
	"os"
	"path/filepath"
	"regexp"
	"slices"
	"strings"

	"gopkg.in/yaml.v3"
)

type mappingDocument struct {
	Metadata struct {
		Module        string `yaml:"module"`
		ModuleVersion string `yaml:"moduleVersion"`
	} `yaml:"metadata"`
	Go struct {
		Calls []mappingCall `yaml:"calls"`
	} `yaml:"go"`
}

type mappingCall struct {
	ID            string        `yaml:"id"`
	Symbol        mappingSymbol `yaml:"symbol"`
	ReceiverState string        `yaml:"receiverState"`
	ArgumentState *struct {
		StateType string `yaml:"stateType"`
		Argument  struct {
			Parameter string `yaml:"parameter"`
			Position  *int   `yaml:"position"`
		} `yaml:"argument"`
	} `yaml:"argumentState"`
	OperationBindings map[string]mappingValueSource `yaml:"operationBindings"`
	Produces          *struct {
		StateType          string                        `yaml:"stateType"`
		DependencyIdentity string                        `yaml:"dependencyIdentity"`
		Bindings           map[string]mappingValueSource `yaml:"bindings"`
	} `yaml:"produces"`
}

type mappingSymbol struct {
	Package  string `yaml:"package"`
	Function string `yaml:"function"`
	Receiver string `yaml:"receiver"`
	Method   string `yaml:"method"`
}

type mappingValueSource struct {
	Argument *struct {
		Parameter string `yaml:"parameter"`
		Position  *int   `yaml:"position"`
		Field     string `yaml:"field"`
	} `yaml:"argument"`
	State string `yaml:"state"`
}

type surfaceSymbol struct {
	parameterNames []string
	parameters     []ast.Expr
}

type packageSurface struct {
	symbols map[string]surfaceSymbol
	structs map[string]map[string]bool
}

type coveragePolicy struct {
	SchemaVersion int `yaml:"schemaVersion"`
	Metadata      struct {
		Module string `yaml:"module"`
	} `yaml:"metadata"`
	Scopes     []coverageScope     `yaml:"scopes"`
	Exclusions []coverageExclusion `yaml:"exclusions"`
	Deferred   []coverageExclusion `yaml:"deferred"`
}

type coverageScope struct {
	Package          string   `yaml:"package"`
	Functions        []string `yaml:"functions"`
	FunctionPatterns []string `yaml:"functionPatterns"`
	Receivers        []string `yaml:"receivers"`
}

type coverageExclusion struct {
	Package   string   `yaml:"package"`
	Receiver  string   `yaml:"receiver"`
	Methods   []string `yaml:"methods"`
	Functions []string `yaml:"functions"`
	Reason    string   `yaml:"reason"`
}

type coverageRecord struct {
	Symbol string `yaml:"symbol"`
	Status string `yaml:"status"`
	CallID string `yaml:"callId,omitempty"`
	Reason string `yaml:"reason,omitempty"`
}

type coverageReport struct {
	SchemaVersion int `yaml:"schemaVersion"`
	Metadata      struct {
		Module        string `yaml:"module"`
		ModuleVersion string `yaml:"moduleVersion"`
	} `yaml:"metadata"`
	Summary struct {
		Scoped       int `yaml:"scoped"`
		Mapped       int `yaml:"mapped"`
		Excluded     int `yaml:"excluded"`
		Deferred     int `yaml:"deferred"`
		Unclassified int `yaml:"unclassified"`
	} `yaml:"summary"`
	Symbols []coverageRecord `yaml:"symbols"`
}

func main() {
	sdkRoot := flag.String("sdk-root", "", "root of the NATS Go module source")
	mappingPath := flag.String("mapping", "", "generated Runtime Conditions SDK mapping")
	coveragePolicyPath := flag.String("coverage-policy", "", "maintenance-only public-surface classification policy")
	coverageOutputPath := flag.String("coverage-output", "", "write deterministic public-surface coverage report")
	allowAbsentPolicySymbols := flag.Bool("allow-absent-policy-symbols", false, "allow a later release policy to contain classifications for symbols absent from this source release")
	flag.Parse()
	if *sdkRoot == "" || *mappingPath == "" {
		exitf("--sdk-root and --mapping are required")
	}
	mapping := readMapping(*mappingPath)
	module := readModulePath(filepath.Join(*sdkRoot, "go.mod"))
	if module != mapping.Metadata.Module {
		exitf("mapping module %q does not match source module %q", mapping.Metadata.Module, module)
	}
	packages := collectSurface(*sdkRoot, module)
	producedStates := make(map[string]bool)
	for _, call := range mapping.Go.Calls {
		pkg := packages[call.Symbol.Package]
		if pkg == nil {
			exitf("%s: package %s does not exist", call.ID, call.Symbol.Package)
		}
		key := symbolKey(call.Symbol)
		symbol, ok := pkg.symbols[key]
		if !ok {
			exitf("%s: source symbol %s was not found", call.ID, key)
		}
		validateSources(call.ID, call.OperationBindings, symbol, pkg, packages)
		if call.ArgumentState != nil {
			if call.ArgumentState.StateType == "" {
				exitf("%s: argumentState.stateType is required", call.ID)
			}
			validateArgument(call.ID+" argumentState", call.ArgumentState.Argument.Parameter, call.ArgumentState.Argument.Position, symbol)
		}
		if call.Produces != nil {
			if call.Produces.StateType == "" {
				exitf("%s: produces.stateType is required", call.ID)
			}
			validateSources(call.ID+" produces", call.Produces.Bindings, symbol, pkg, packages)
			producedStates[call.Produces.StateType] = true
		}
	}
	for _, call := range mapping.Go.Calls {
		if call.ReceiverState != "" && !producedStates[call.ReceiverState] {
			exitf("%s: receiverState %s is never produced", call.ID, call.ReceiverState)
		}
	}
	if *coveragePolicyPath != "" {
		policy := readCoveragePolicy(*coveragePolicyPath)
		if policy.Metadata.Module != module {
			exitf("coverage policy module %q does not match source module %q", policy.Metadata.Module, module)
		}
		report, unclassified, absent := classifyCoverage(policy, mapping, packages, *allowAbsentPolicySymbols)
		if *coverageOutputPath != "" {
			writeCoverageReport(*coverageOutputPath, report)
		}
		if len(unclassified) != 0 {
			exitf("unclassified public SDK operations:\n  %s", strings.Join(unclassified, "\n  "))
		}
		fmt.Printf("coverage: %d mapped, %d excluded, %d deferred, %d unclassified\n", report.Summary.Mapped, report.Summary.Excluded, report.Summary.Deferred, report.Summary.Unclassified)
		if len(absent) != 0 {
			fmt.Printf("policy symbols absent from source: %d\n", len(absent))
			for _, symbol := range absent {
				fmt.Printf("  %s\n", symbol)
			}
		}
	}
	fmt.Printf("module: %s %s\n", mapping.Metadata.Module, mapping.Metadata.ModuleVersion)
	fmt.Printf("validated calls: %d\n", len(mapping.Go.Calls))
	fmt.Printf("produced state types: %d\n", len(producedStates))
}

func validateArgument(id string, parameter string, configuredPosition *int, symbol surfaceSymbol) int {
	position := -1
	if parameter != "" {
		position = slices.Index(symbol.parameterNames, parameter)
		if position < 0 {
			exitf("%s points at missing parameter %q; available parameters: %s", id, parameter, strings.Join(symbol.parameterNames, ", "))
		}
	} else if configuredPosition != nil {
		position = *configuredPosition
	} else {
		exitf("%s requires argument.parameter or argument.position", id)
	}
	if position < 0 || position >= len(symbol.parameters) {
		exitf("%s points at argument %d but symbol has %d arguments", id, position, len(symbol.parameters))
	}
	return position
}

func readCoveragePolicy(path string) coveragePolicy {
	data, err := os.ReadFile(path)
	if err != nil {
		exitf("%v", err)
	}
	var policy coveragePolicy
	if err := yaml.Unmarshal(data, &policy); err != nil {
		exitf("%s: %v", path, err)
	}
	if policy.SchemaVersion != 1 || policy.Metadata.Module == "" || len(policy.Scopes) == 0 {
		exitf("%s: schemaVersion 1, metadata.module, and scopes are required", path)
	}
	return policy
}

func readMapping(path string) mappingDocument {
	data, err := os.ReadFile(path)
	if err != nil {
		exitf("%v", err)
	}
	var document mappingDocument
	if err := yaml.Unmarshal(data, &document); err != nil {
		exitf("%s: %v", path, err)
	}
	return document
}

func readModulePath(path string) string {
	data, err := os.ReadFile(path)
	if err != nil {
		exitf("%v", err)
	}
	match := regexp.MustCompile(`(?m)^module\s+(\S+)\s*$`).FindStringSubmatch(string(data))
	if len(match) != 2 {
		exitf("%s: module directive not found", path)
	}
	return match[1]
}

func collectSurface(root string, module string) map[string]*packageSurface {
	result := make(map[string]*packageSurface)
	err := filepath.WalkDir(root, func(path string, entry os.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if entry.IsDir() {
			if entry.Name() == ".git" || entry.Name() == "vendor" || entry.Name() == "test" || entry.Name() == "examples" {
				return filepath.SkipDir
			}
			return nil
		}
		if !strings.HasSuffix(path, ".go") || strings.HasSuffix(path, "_test.go") {
			return nil
		}
		relative, err := filepath.Rel(root, filepath.Dir(path))
		if err != nil {
			return err
		}
		importPath := module
		if relative != "." {
			importPath += "/" + filepath.ToSlash(relative)
		}
		pkg := result[importPath]
		if pkg == nil {
			pkg = &packageSurface{symbols: make(map[string]surfaceSymbol), structs: make(map[string]map[string]bool)}
			result[importPath] = pkg
		}
		file, err := parser.ParseFile(token.NewFileSet(), path, nil, 0)
		if err != nil {
			return err
		}
		collectFile(pkg, file)
		return nil
	})
	if err != nil {
		exitf("%v", err)
	}
	return result
}

func collectFile(pkg *packageSurface, file *ast.File) {
	for _, declaration := range file.Decls {
		switch typed := declaration.(type) {
		case *ast.FuncDecl:
			key := typed.Name.Name
			if typed.Recv != nil && len(typed.Recv.List) > 0 {
				key = receiverName(typed.Recv.List[0].Type) + "." + typed.Name.Name
			}
			names, types := parameters(typed.Type.Params)
			pkg.symbols[key] = surfaceSymbol{parameterNames: names, parameters: types}
		case *ast.GenDecl:
			if typed.Tok != token.TYPE {
				continue
			}
			for _, spec := range typed.Specs {
				typeSpec, ok := spec.(*ast.TypeSpec)
				if !ok {
					continue
				}
				switch value := typeSpec.Type.(type) {
				case *ast.StructType:
					fields := make(map[string]bool)
					for _, field := range value.Fields.List {
						for _, name := range field.Names {
							fields[name.Name] = true
						}
					}
					pkg.structs[typeSpec.Name.Name] = fields
				case *ast.InterfaceType:
					for _, field := range value.Methods.List {
						function, ok := field.Type.(*ast.FuncType)
						if !ok {
							continue
						}
						names, types := parameters(function.Params)
						for _, name := range field.Names {
							pkg.symbols[typeSpec.Name.Name+"."+name.Name] = surfaceSymbol{parameterNames: names, parameters: types}
						}
					}
				}
			}
		}
	}
}

func parameters(fields *ast.FieldList) ([]string, []ast.Expr) {
	if fields == nil {
		return nil, nil
	}
	var names []string
	var types []ast.Expr
	for _, field := range fields.List {
		count := len(field.Names)
		if count == 0 {
			count = 1
		}
		for index := range count {
			name := ""
			if index < len(field.Names) {
				name = field.Names[index].Name
			}
			names = append(names, name)
			types = append(types, field.Type)
		}
	}
	return names, types
}

func validateSources(id string, sources map[string]mappingValueSource, symbol surfaceSymbol, pkg *packageSurface, packages map[string]*packageSurface) {
	fields := make([]string, 0, len(sources))
	for field := range sources {
		fields = append(fields, field)
	}
	slices.Sort(fields)
	for _, target := range fields {
		source := sources[target]
		if source.State != "" {
			continue
		}
		if source.Argument == nil {
			exitf("%s: binding %s requires argument or state", id, target)
		}
		position := validateArgument(id+" binding "+target, source.Argument.Parameter, source.Argument.Position, symbol)
		if source.Argument.Field == "" {
			continue
		}
		typeName := receiverName(symbol.parameters[position])
		if !surfaceHasField(pkg, packages, typeName, source.Argument.Field) {
			exitf("%s: binding %s points at missing field %s.%s", id, target, typeName, source.Argument.Field)
		}
	}
}

func surfaceHasField(pkg *packageSurface, packages map[string]*packageSurface, typeName string, field string) bool {
	if pkg.structs[typeName][field] {
		return true
	}
	for _, candidate := range packages {
		if candidate.structs[typeName][field] {
			return true
		}
	}
	return false
}

func classifyCoverage(policy coveragePolicy, mapping mappingDocument, packages map[string]*packageSurface, allowAbsentPolicySymbols bool) (coverageReport, []string, []string) {
	mapped := make(map[string]string)
	for _, call := range mapping.Go.Calls {
		mapped[qualifiedSymbol(call.Symbol)] = call.ID
	}
	excluded := coverageClassifications(policy.Exclusions, "exclusion")
	deferred := coverageClassifications(policy.Deferred, "deferred classification")
	for key := range deferred {
		if _, exists := excluded[key]; exists {
			exitf("coverage symbol %s is both excluded and deferred", key)
		}
	}
	scoped := make(map[string]bool)
	for _, scope := range policy.Scopes {
		pkg := packages[scope.Package]
		if pkg == nil {
			exitf("coverage scope package %s does not exist", scope.Package)
		}
		for _, function := range scope.Functions {
			if _, ok := pkg.symbols[function]; !ok {
				exitf("coverage scope function %s::%s does not exist", scope.Package, function)
			}
			scoped[scope.Package+"::"+function] = true
		}
		for _, patternText := range scope.FunctionPatterns {
			pattern, err := regexp.Compile(patternText)
			if err != nil {
				exitf("coverage function pattern %q: %v", patternText, err)
			}
			for key := range pkg.symbols {
				if !strings.Contains(key, ".") && ast.IsExported(key) && pattern.MatchString(key) {
					scoped[scope.Package+"::"+key] = true
				}
			}
		}
		for _, receiver := range scope.Receivers {
			prefix := receiver + "."
			found := false
			for key := range pkg.symbols {
				if strings.HasPrefix(key, prefix) && ast.IsExported(strings.TrimPrefix(key, prefix)) {
					scoped[scope.Package+"::"+key] = true
					found = true
				}
			}
			if !found {
				exitf("coverage receiver %s::%s has no exported methods", scope.Package, receiver)
			}
		}
	}
	keys := make([]string, 0, len(scoped))
	for key := range scoped {
		keys = append(keys, key)
	}
	slices.Sort(keys)
	var report coverageReport
	report.SchemaVersion = 1
	report.Metadata.Module = mapping.Metadata.Module
	report.Metadata.ModuleVersion = mapping.Metadata.ModuleVersion
	var unclassified []string
	for _, key := range keys {
		record := coverageRecord{Symbol: key}
		if callID := mapped[key]; callID != "" {
			record.Status = "mapped"
			record.CallID = callID
			report.Summary.Mapped++
		} else if reason := excluded[key]; reason != "" {
			record.Status = "excluded"
			record.Reason = reason
			report.Summary.Excluded++
		} else if reason := deferred[key]; reason != "" {
			record.Status = "deferred"
			record.Reason = reason
			report.Summary.Deferred++
		} else {
			record.Status = "unclassified"
			report.Summary.Unclassified++
			unclassified = append(unclassified, key)
		}
		report.Symbols = append(report.Symbols, record)
	}
	report.Summary.Scoped = len(report.Symbols)
	var absent []string
	for key := range excluded {
		if !scoped[key] {
			if !allowAbsentPolicySymbols {
				exitf("coverage exclusion %s is not present in the scoped SDK surface", key)
			}
			absent = append(absent, key)
		}
	}
	for key := range deferred {
		if !scoped[key] {
			if !allowAbsentPolicySymbols {
				exitf("deferred coverage symbol %s is not present in the scoped SDK surface", key)
			}
			absent = append(absent, key)
		}
	}
	slices.Sort(absent)
	return report, unclassified, absent
}

func coverageClassifications(entries []coverageExclusion, label string) map[string]string {
	classified := make(map[string]string)
	for _, entry := range entries {
		if entry.Package == "" || entry.Reason == "" || (len(entry.Functions) == 0 && (entry.Receiver == "" || len(entry.Methods) == 0)) {
			exitf("coverage %s entries require package, reason, and functions or receiver methods", label)
		}
		for _, function := range entry.Functions {
			key := entry.Package + "::" + function
			if _, exists := classified[key]; exists {
				exitf("duplicate coverage %s for %s", label, key)
			}
			classified[key] = entry.Reason
		}
		for _, method := range entry.Methods {
			key := entry.Package + "::" + entry.Receiver + "." + method
			if _, exists := classified[key]; exists {
				exitf("duplicate coverage %s for %s", label, key)
			}
			classified[key] = entry.Reason
		}
	}
	return classified
}

func qualifiedSymbol(symbol mappingSymbol) string {
	return symbol.Package + "::" + symbolKey(symbol)
}

func writeCoverageReport(path string, report coverageReport) {
	data, err := yaml.Marshal(report)
	if err != nil {
		exitf("marshal coverage report: %v", err)
	}
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		exitf("create coverage report directory: %v", err)
	}
	if err := os.WriteFile(path, data, 0o644); err != nil {
		exitf("write coverage report: %v", err)
	}
}

func receiverName(expression ast.Expr) string {
	switch typed := expression.(type) {
	case *ast.Ident:
		return typed.Name
	case *ast.SelectorExpr:
		return typed.Sel.Name
	case *ast.StarExpr:
		return receiverName(typed.X)
	case *ast.IndexExpr:
		return receiverName(typed.X)
	case *ast.IndexListExpr:
		return receiverName(typed.X)
	case *ast.Ellipsis:
		return receiverName(typed.Elt)
	default:
		return ""
	}
}

func symbolKey(symbol mappingSymbol) string {
	if symbol.Function != "" {
		return symbol.Function
	}
	return symbol.Receiver + "." + symbol.Method
}

func exitf(format string, args ...any) {
	fmt.Fprintf(os.Stderr, "runtimeconditions: "+format+"\n", args...)
	os.Exit(1)
}
