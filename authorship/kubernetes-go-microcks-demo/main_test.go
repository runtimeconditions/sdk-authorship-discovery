package main

import (
	"errors"
	"io"
	"net/http"
	"strings"
	"testing"
)

type transportFunc func(*http.Request) (*http.Response, error)

func (f transportFunc) RoundTrip(r *http.Request) (*http.Response, error) { return f(r) }
func TestRecorderClonesAndCaptures(t *testing.T) {
	original, _ := http.NewRequest("GET", "http://127.0.0.1/private?secret=not-recorded", nil)
	original.Header.Set("Authorization", "not-recorded")
	recorder := &Recorder{TraceID: "0123456789abcdef0123456789abcdef", ParentSpanID: "0123456789abcdef", Next: transportFunc(func(r *http.Request) (*http.Response, error) {
		if r.Header.Get("X-Trace-Id") != "0123456789abcdef0123456789abcdef" {
			t.Fatal("trace not propagated")
		}
		if r.Header.Get("traceparent") != "00-0123456789abcdef0123456789abcdef-0123456789abcdef-01" {
			t.Fatal("traceparent not propagated")
		}
		return &http.Response{StatusCode: 200, Body: io.NopCloser(strings.NewReader("not-recorded"))}, nil
	})}
	response, err := recorder.RoundTrip(original)
	if err != nil {
		t.Fatal(err)
	}
	response.Body.Close()
	if original.Header.Get("X-Trace-Id") != "" {
		t.Fatal("original request mutated")
	}
	if len(recorder.Requests) != 1 || !recorder.Requests[0].HasQuery || recorder.Requests[0].Status != 200 || recorder.Requests[0].Path != "/private" {
		t.Fatal(recorder.Requests)
	}
}
func TestRecorderTransportFailure(t *testing.T) {
	recorder := &Recorder{Next: transportFunc(func(*http.Request) (*http.Response, error) { return nil, errors.New("private error") })}
	req, _ := http.NewRequest("GET", "http://127.0.0.1/failure", nil)
	_, err := recorder.RoundTrip(req)
	if err == nil || len(recorder.Requests) != 1 || !recorder.Requests[0].TransportError || recorder.Requests[0].Status != 0 {
		t.Fatal("lost failure evidence")
	}
}
