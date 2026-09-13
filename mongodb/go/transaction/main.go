package main

import (
	"context"
	"log"
	"os"

	"go.mongodb.org/mongo-driver/v2/bson"
	"go.mongodb.org/mongo-driver/v2/mongo"
	"go.mongodb.org/mongo-driver/v2/mongo/options"
)

func transfer(ctx context.Context, client *mongo.Client, source string, destination string, amount int) error {
	accounts := client.Database("billing").Collection("accounts")
	ledger := client.Database("billing").Collection("ledger")
	session, err := client.StartSession()
	if err != nil {
		return err
	}
	defer session.EndSession(ctx)

	_, err = session.WithTransaction(ctx, func(transactionContext context.Context) (any, error) {
		if _, err := accounts.UpdateOne(transactionContext, bson.D{{Key: "account", Value: source}}, bson.D{{Key: "$inc", Value: bson.D{{Key: "balance", Value: -amount}}}}); err != nil {
			return nil, err
		}
		if _, err := accounts.UpdateOne(transactionContext, bson.D{{Key: "account", Value: destination}}, bson.D{{Key: "$inc", Value: bson.D{{Key: "balance", Value: amount}}}}); err != nil {
			return nil, err
		}
		return ledger.InsertOne(transactionContext, bson.D{{Key: "source", Value: source}, {Key: "destination", Value: destination}, {Key: "amount", Value: amount}})
	})
	return err
}

func run(ctx context.Context, uri string) error {
	client, err := mongo.Connect(options.Client().ApplyURI(uri))
	if err != nil {
		return err
	}
	defer client.Disconnect(ctx)
	return transfer(ctx, client, "checking", "savings", 250)
}

func main() {
	if err := run(context.Background(), os.Getenv("MONGODB_URI")); err != nil {
		log.Fatal(err)
	}
}
