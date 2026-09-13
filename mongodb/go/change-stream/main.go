package main

import (
	"context"
	"log"
	"os"

	"go.mongodb.org/mongo-driver/v2/bson"
	"go.mongodb.org/mongo-driver/v2/mongo"
	"go.mongodb.org/mongo-driver/v2/mongo/options"
)

func run(ctx context.Context, uri string) error {
	client, err := mongo.Connect(options.Client().ApplyURI(uri))
	if err != nil {
		return err
	}
	defer client.Disconnect(ctx)

	stock := client.Database("inventory").Collection("stock")
	pipeline := mongo.Pipeline{bson.D{{Key: "$match", Value: bson.D{{Key: "operationType", Value: bson.D{{Key: "$in", Value: bson.A{"insert", "update", "replace"}}}}}}}}
	changes, err := stock.Watch(ctx, pipeline, options.ChangeStream().SetFullDocument(options.UpdateLookup))
	if err != nil {
		return err
	}
	defer changes.Close(ctx)
	for changes.Next(ctx) {
		var change bson.M
		if err := changes.Decode(&change); err != nil {
			return err
		}
		log.Printf("change: %v", change)
	}
	return changes.Err()
}

func main() {
	if err := run(context.Background(), os.Getenv("MONGODB_URI")); err != nil {
		log.Fatal(err)
	}
}
