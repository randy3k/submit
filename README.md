# A simple server to preview private github repo

```
PROJECTID=$(gcloud config get-value project)
```

```
docker build . -t gcr.io/$PROJECTID/submit
```

Test locally
```
docker run --rm -p 8080:8080 gcr.io/$PROJECTID/submit:latest
```

Push image to Google Registry
```
gcloud auth configure-docker
docker push gcr.io/$PROJECTID/submit
```

Alternatively, ultilize Googld Builds to build image
```
gcloud builds submit --tag gcr.io/$PROJECTID/submit
```

Deploy to Google Cloud Run
```
gcloud run deploy --image gcr.io/$PROJECTID/submit --platform managed --max-instances 1
```
