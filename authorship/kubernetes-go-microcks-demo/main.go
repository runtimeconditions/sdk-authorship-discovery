// This executable invokes authored SDK fixtures; it is not a mapping generator.
package main

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"net/http"
	"net/url"
	"os"
	"strings"
	"time"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
)

type Request struct {
	Method         string `json:"method"`
	Path           string `json:"path"`
	HasQuery       bool   `json:"hasQuery"`
	Status         int    `json:"status"`
	TransportError bool   `json:"transportError"`
}
type Recorder struct {
	Next         http.RoundTripper
	TraceID      string
	ParentSpanID string
	Requests     []Request
}

func (r *Recorder) RoundTrip(req *http.Request) (*http.Response, error) {
	clone := req.Clone(req.Context())
	clone.Header = req.Header.Clone()
	clone.Header.Set("X-Trace-Id", r.TraceID)
	if r.ParentSpanID != "" {
		clone.Header.Set("traceparent", "00-"+r.TraceID+"-"+r.ParentSpanID+"-01")
	}
	response, err := r.Next.RoundTrip(clone)
	record := Request{Method: req.Method, Path: req.URL.EscapedPath(), HasQuery: req.URL.RawQuery != "", TransportError: err != nil}
	if response != nil {
		record.Status = response.StatusCode
	}
	r.Requests = append(r.Requests, record)
	return response, err
}

type Invocation struct {
	Case             string    `json:"case"`
	SDKMethod        string    `json:"sdkMethod"`
	TraceID          string    `json:"traceId"`
	Requests         []Request `json:"requests"`
	SDKSuccess       bool      `json:"sdkSuccess"`
	ResponseVerified bool      `json:"responseVerified"`
}

func invoke(ctx context.Context, host, service, name string) (Invocation, error) {
	trace := make([]byte, 16)
	if _, err := rand.Read(trace); err != nil {
		return Invocation{}, err
	}
	parentSpan := make([]byte, 8)
	if _, err := rand.Read(parentSpan); err != nil {
		return Invocation{}, err
	}
	out := Invocation{Case: name, TraceID: hex.EncodeToString(trace)}
	var recorder *Recorder
	// Config.Timeout adds a query parameter to Get; bound the call with context instead.
	ctx, cancel := context.WithTimeout(ctx, 10*time.Second)
	defer cancel()
	config := &rest.Config{Host: strings.TrimRight(host, "/") + "/rest/" + service + "/v1.36.2"}
	config.WrapTransport = func(next http.RoundTripper) http.RoundTripper {
		recorder = &Recorder{Next: next, TraceID: out.TraceID, ParentSpanID: hex.EncodeToString(parentSpan)}
		return recorder
	}
	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		return out, err
	}
	switch name {
	case "pod-list":
		out.SDKMethod = "k8s.io/client-go/kubernetes/typed/core/v1.PodInterface.List"
		pods, callErr := clientset.CoreV1().Pods("demo").List(ctx, metav1.ListOptions{})
		out.SDKSuccess = callErr == nil
		out.ResponseVerified = callErr == nil && pods.Items != nil && len(pods.Items) == 0
	case "configmap-get":
		out.SDKMethod = "k8s.io/client-go/kubernetes/typed/core/v1.ConfigMapInterface.Get"
		cm, callErr := clientset.CoreV1().ConfigMaps("demo").Get(ctx, "settings", metav1.GetOptions{})
		out.SDKSuccess = callErr == nil
		out.ResponseVerified = callErr == nil && cm.Name == "settings" && cm.Namespace == "demo" && cm.Data["source"] == "microcks-fixture"
	default:
		return out, errors.New("unsupported fixture")
	}
	if recorder == nil {
		return out, errors.New("transport was not constructed")
	}
	out.Requests = recorder.Requests
	return out, nil
}
func main() {
	host := flag.String("host", "http://127.0.0.1:8080", "isolated local Microcks URL")
	service := flag.String("service", "rc-kubernetes-core", "imported fixture service")
	name := flag.String("case", "pod-list", "pod-list or configmap-get")
	flag.Parse()
	trimmedHost := strings.TrimRight(*host, "/")
	u, err := url.Parse(trimmedHost)
	if err != nil || u.Scheme != "http" || u.Hostname() != "127.0.0.1" || u.User != nil || u.RawQuery != "" || u.Fragment != "" || u.Path != "" {
		fmt.Fprintln(os.Stderr, "host must be http://127.0.0.1:<port>")
		os.Exit(1)
	}
	if *service != "rc-kubernetes-core" && *service != "rc-kubernetes-sparse" && *service != "rc-kubernetes-malformed" {
		fmt.Fprintln(os.Stderr, "unsupported fixture service")
		os.Exit(1)
	}
	result, err := invoke(context.Background(), trimmedHost, *service, *name)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	if err = json.NewEncoder(os.Stdout).Encode(result); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
