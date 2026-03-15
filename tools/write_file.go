package tools

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"google.golang.org/genai"
)

var WriteFile = Tool{
	Name:        "write_file",
	Description: "Write content to a file at the given path. Creates the file if it doesn't exist, overwrites if it does.",
	Parameters: &genai.Schema{
		Type: genai.TypeObject,
		Properties: map[string]*genai.Schema{
			"path": {
				Type:        genai.TypeString,
				Description: "Relative file path",
			},
			"content": {
				Type:        genai.TypeString,
				Description: "Content to write to the file",
			},
		},
		Required: []string{"path", "content"},
	},
	Execute: func(args map[string]any) any {
		path := args["path"].(string)
		content := args["content"].(string)
		
		finalPath := path
		if _, err := os.Stat(finalPath); err == nil {
			ext := filepath.Ext(path)
			base := strings.TrimSuffix(path, ext)
			for i := 1; ; i++ {
				finalPath = fmt.Sprintf("%s_%d%s", base, i, ext)
				if _, err := os.Stat(finalPath); os.IsNotExist(err) {
					break
				}
			}
		}
		
		err := os.WriteFile(finalPath, []byte(content), 0644)
		if err != nil {
			return fmt.Sprintf("Error: %s", err.Error())
		}
		return fmt.Sprintf("Successfully wrote to %s", finalPath)
	},
}
