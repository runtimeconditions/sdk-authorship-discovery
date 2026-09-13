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

	orders := client.Database("commerce").Collection("orders")
	result, err := orders.InsertOne(ctx, bson.D{{Key: "status", Value: "pending"}, {Key: "total", Value: 1250}})
	if err != nil {
		return err
	}
	if err := orders.FindOne(ctx, bson.D{{Key: "_id", Value: result.InsertedID}}).Err(); err != nil {
		return err
	}
	if _, err := orders.UpdateOne(ctx, bson.D{{Key: "_id", Value: result.InsertedID}}, bson.D{{Key: "$set", Value: bson.D{{Key: "status", Value: "paid"}}}}); err != nil {
		return err
	}
	_, err = orders.DeleteOne(ctx, bson.D{{Key: "_id", Value: result.InsertedID}})
	return err
}

func main() {
	if err := run(context.Background(), os.Getenv("MONGODB_URI")); err != nil {
		log.Fatal(err)
	}
}
