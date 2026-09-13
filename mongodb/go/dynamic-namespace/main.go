package main

import (
	"context"
	"log"
	"os"

	"go.mongodb.org/mongo-driver/v2/bson"
	"go.mongodb.org/mongo-driver/v2/mongo"
	"go.mongodb.org/mongo-driver/v2/mongo/options"
)

func run(ctx context.Context, uri string, databaseName string, collectionName string) error {
	client, err := mongo.Connect(options.Client().ApplyURI(uri))
	if err != nil {
		return err
	}
	defer client.Disconnect(ctx)
	return client.Database(databaseName).Collection(collectionName).FindOne(ctx, bson.D{{Key: "enabled", Value: true}}).Err()
}

func main() {
	if err := run(context.Background(), os.Getenv("MONGODB_URI"), os.Getenv("MONGODB_DATABASE"), os.Getenv("MONGODB_COLLECTION")); err != nil {
		log.Fatal(err)
	}
}
