package main

import (
	"context"
	"log"
	"os"

	"go.mongodb.org/mongo-driver/v2/bson"
	"go.mongodb.org/mongo-driver/v2/mongo"
	"go.mongodb.org/mongo-driver/v2/mongo/options"
)

func ordersCollection(client *mongo.Client) *mongo.Collection {
	return client.Database("commerce").Collection("orders")
}

func createOrder(ctx context.Context, collection *mongo.Collection, order any) error {
	_, err := collection.InsertOne(ctx, order)
	return err
}

func run(ctx context.Context, uri string) error {
	client, err := mongo.Connect(options.Client().ApplyURI(uri))
	if err != nil {
		return err
	}
	defer client.Disconnect(ctx)
	return createOrder(ctx, ordersCollection(client), bson.D{{Key: "status", Value: "pending"}, {Key: "total", Value: 1250}})
}

func main() {
	if err := run(context.Background(), os.Getenv("MONGODB_URI")); err != nil {
		log.Fatal(err)
	}
}
