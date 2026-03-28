package tools

import "google.golang.org/genai"

type Tool struct {
	Name        string
	Description string
	Parameters  *genai.Schema
	Execute     func(args map[string]any) any
}
