package main

import (
	"context"
	"log"
	"os"

	"go.mongodb.org/mongo-driver/v2/mongo"
	"go.mongodb.org/mongo-driver/v2/mongo/options"
)

func buildClient(uri string) (*mongo.Client, error) {
	return mongo.Connect(options.Client().ApplyURI(uri))
}

func main() {
	client, err := buildClient(os.Getenv("MONGODB_URI"))
	if err != nil {
		log.Fatal(err)
	}
	if err := client.Disconnect(context.Background()); err != nil {
		log.Fatal(err)
	}
}
