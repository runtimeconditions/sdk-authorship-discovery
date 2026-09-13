package main

import (
	"bytes"
	"context"
	"log"
	"os"

	"go.mongodb.org/mongo-driver/v2/mongo"
	"go.mongodb.org/mongo-driver/v2/mongo/options"
)

func run(ctx context.Context, uri string) error {
	client, err := mongo.Connect(options.Client().ApplyURI(uri))
	if err != nil {
		return err
	}
	defer client.Disconnect(ctx)

	bucket := client.Database("media").GridFSBucket(options.GridFSBucket().SetName("assets"))
	fileID, err := bucket.UploadFromStream(ctx, "logo.svg", bytes.NewBufferString("<svg></svg>"))
	if err != nil {
		return err
	}
	downloaded := new(bytes.Buffer)
	if _, err := bucket.DownloadToStream(ctx, fileID, downloaded); err != nil {
		return err
	}
	return bucket.Delete(ctx, fileID)
}

func main() {
	if err := run(context.Background(), os.Getenv("MONGODB_URI")); err != nil {
		log.Fatal(err)
	}
}
