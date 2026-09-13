package main

import (
	"context"
	"log"
	"os"

	"go.mongodb.org/mongo-driver/v2/bson"
	"go.mongodb.org/mongo-driver/v2/mongo"
	"go.mongodb.org/mongo-driver/v2/mongo/options"
)

func run(ctx context.Context, analyticsURI string, operationalURI string) error {
	analytics, err := mongo.Connect(options.Client().ApplyURI(analyticsURI))
	if err != nil {
		return err
	}
	defer analytics.Disconnect(ctx)
	operational, err := mongo.Connect(options.Client().ApplyURI(operationalURI))
	if err != nil {
		return err
	}
	defer operational.Disconnect(ctx)

	if _, err := analytics.Database("warehouse").Collection("events").InsertOne(ctx, bson.D{{Key: "type", Value: "order.created"}}); err != nil {
		return err
	}
	return operational.Database("commerce").Collection("orders").FindOne(ctx, bson.D{{Key: "status", Value: "pending"}}).Err()
}

func main() {
	if err := run(context.Background(), os.Getenv("MONGODB_ANALYTICS_URI"), os.Getenv("MONGODB_OPERATIONAL_URI")); err != nil {
		log.Fatal(err)
	}
}
