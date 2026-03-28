package main

import (
	"bufio"
	"context"
	"fmt"
	"os"

	"github.com/arjunpathak072/clanker/tools"
	"github.com/joho/godotenv"
	"google.golang.org/genai"
)

func main() {
	godotenv.Load()
	ctx := context.Background()
	client, err := genai.NewClient(ctx, nil)
	if err != nil {
		fmt.Printf("Error: %s\n", err.Error())
		return
	}

	scanner := bufio.NewScanner(os.Stdin)
	getUserMessage := func() (string, bool) {
		if !scanner.Scan() {
			return "", false
		}
		return scanner.Text(), true
	}

	agent := NewAgent(client, getUserMessage, []tools.Tool{tools.WriteFile})
	err = agent.Run(context.TODO())
	if err != nil {
		fmt.Printf("Error: %s\n", err.Error())
	}
}

func NewAgent(client *genai.Client, getUserMessage func() (string, bool), toolsList []tools.Tool) *Agent {
	return &Agent{
		client:         client,
		getUserMessage: getUserMessage,
		tools:          toolsList,
	}
}

type Agent struct {
	client         *genai.Client
	getUserMessage func() (string, bool)
	tools          []tools.Tool
}

func (a *Agent) executeFunction(name string, args map[string]any) any {
	for _, tool := range a.tools {
		if tool.Name == name {
			return tool.Execute(args)
		}
	}
	return map[string]string{"error": "unknown function"}
}

func (a *Agent) Run(ctx context.Context) error {
	conversation := []*genai.Content{}

	fmt.Println("Chat with Gemini (use 'ctrl-c' to quit)")

	for {
		fmt.Print("\u001b[94mYou\u001b[0m: ")
		userInput, ok := a.getUserMessage()
		if !ok {
			break
		}

		userMessage := &genai.Content{
			Role:  "user",
			Parts: []*genai.Part{{Text: userInput}},
		}
		conversation = append(conversation, userMessage)

		message, err := a.runInference(ctx, conversation)
		if err != nil {
			return err
		}
		conversation = append(conversation, message.Candidates[0].Content)

		hasFunctionCall := false
		for _, part := range message.Candidates[0].Content.Parts {
			if part.FunctionCall != nil {
				hasFunctionCall = true
				fmt.Printf("\u001b[95mTool\u001b[0m: %s(%v)\n", part.FunctionCall.Name, part.FunctionCall.Args)
				result := a.executeFunction(part.FunctionCall.Name, part.FunctionCall.Args)
				conversation = append(conversation, &genai.Content{
					Role: "function",
					Parts: []*genai.Part{{
						FunctionResponse: &genai.FunctionResponse{
							Name:     part.FunctionCall.Name,
							Response: map[string]any{"result": result},
						},
					}},
				})
			}
		}

		if hasFunctionCall {
			message, err = a.runInference(ctx, conversation)
			if err != nil {
				return err
			}
			conversation = append(conversation, message.Candidates[0].Content)
		}

		if message.Text() != "" {
			fmt.Printf("\u001b[93mGemini\u001b[0m: %s\n", message.Text())
		}
	}

	return nil
}

func (a *Agent) runInference(ctx context.Context, conversation []*genai.Content) (*genai.GenerateContentResponse, error) {
	gemini_tools := []*genai.Tool{}
	for _, tool := range a.tools {
		gemini_tools = append(gemini_tools, &genai.Tool{
			FunctionDeclarations: []*genai.FunctionDeclaration{
				{
					Name:        tool.Name,
					Description: tool.Description,
					Parameters:  tool.Parameters,
				},
			},
		})
	}
	message, err := a.client.Models.GenerateContent(ctx, "gemini-3-flash-preview", conversation, &genai.GenerateContentConfig{
		Tools: gemini_tools,
	})
	return message, err
}
