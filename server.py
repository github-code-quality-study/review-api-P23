import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from nltk.corpus import stopwords
from urllib.parse import parse_qs, urlparse
import json
import pandas as pd
from datetime import datetime
import uuid
import os
from typing import Callable, Any
from wsgiref.simple_server import make_server

nltk.download('vader_lexicon', quiet=True)
nltk.download('punkt', quiet=True)
nltk.download('averaged_perceptron_tagger', quiet=True)
nltk.download('stopwords', quiet=True)

adj_noun_pairs_count = {}
sia = SentimentIntensityAnalyzer()
stop_words = set(stopwords.words('english'))

reviews = pd.read_csv('data/reviews.csv').to_dict('records')

class ReviewAnalyzerServer:
    def __init__(self) -> None:
        # This method is a placeholder for future initialization logic
        #initialize the reviews data 
        self.reviews = pd.read_csv('data/reviews.csv').to_dict('records')
        # pass

    def analyze_sentiment(self, review_body): #this works with no modifications.
        sentiment_scores = sia.polarity_scores(review_body)
        return sentiment_scores

    def __call__(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> bytes:
        """
        The environ parameter is a dictionary containing some useful
        HTTP request information such as: REQUEST_METHOD, CONTENT_LENGTH, QUERY_STRING,
        PATH_INFO, CONTENT_TYPE, etc.
        """
        if environ["REQUEST_METHOD"] == "GET":
            # Create the response body from the reviews and convert to a JSON byte string
            response_body = json.dumps(reviews, indent=2).encode("utf-8")
            # Write your code here
            #TASK IS to parse query parameters from query string 
            filtered_reviews = self.reviews 
            try: 
                query_string = environ["QUERY_STRING"] 
                query_params = parse_qs(query_string) #parse_qs returns a dictionary of query parameters

                location = query_params['location'][0]  #shouldnt return None
                if location:
                    filtered_reviews = [review for review in filtered_reviews if review['Location'] == location] 
            
            except: 
                pass

            try: 
                start_date = query_params['start_date'][0] 
                if start_date:
                    filtered_reviews = [review for review in filtered_reviews if start_date <= review['Timestamp']] 
            except:
                pass 

            try:
                end_date = query_params['end_date'][0] 
                if end_date:
                    filtered_reviews = [review for review in filtered_reviews if review['Timestamp'] <= end_date] 
            except:
                pass 

            for review in filtered_reviews: 
                review['sentiment'] = self.analyze_sentiment(review['ReviewBody']) 
            filtered_reviews = sorted(filtered_reviews, key=lambda x: x['sentiment']['compound'], reverse=True) 

            response_body = json.dumps(filtered_reviews, indent=2).encode("utf-8")
            start_response("200 OK", [
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(response_body)))
            ])
            
            return [response_body]


        if environ["REQUEST_METHOD"] == "POST": #post takes 2 arguments, reviewbody and location
            # Write your code here

            ReviewId = str(uuid.uuid4())
            Timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S') 

            content_length = int(environ["CONTENT_LENGTH"]) 
            content_type = environ["CONTENT_TYPE"] 
            #read the body of the request 
            request_body = environ["wsgi.input"].read(content_length) 
            #convert the above bytes information to string 
            request_body = parse_qs(request_body.decode("utf-8"))
            try: 
                review_body = request_body['ReviewBody'][0] #bouth should be there and both should actally be in the review
                location = request_body['Location'][0]
            except: 
                error_message = 'ReviewBody and Location are required fields'
                response_body = json.dumps(error_message, indent=2).encode("utf-8")
                start_response("400 Bad Request", [("Content-Type", "text/plain")]) 
                return [response_body]
            
            #self.reviews is a list of dictionaries, check if location is in the list of dictionaries
            location_exists = any(review.get('Location') == location for review in self.reviews)
            if location_exists:
                pass
            else: 
                error_message  = 'Location not found'
                response_body = json.dumps({'ReviewId': ReviewId, "error": error_message}, indent=2).encode("utf-8")
                start_response("400 Bad Request", [("Content-Type", "application/json"), ("Content-Length", str(len(response_body)))])
                return [response_body]
            new_review = {
                'ReviewBody': review_body, 
                'Location': location, 
                'Timestamp': Timestamp, 
                'ReviewId': ReviewId
            }

            #append this new_review to review
            self.reviews.append(new_review)
            response_body = json.dumps(new_review, indent=2).encode("utf-8")
            start_response("201 Created", [
                ("Content-Type", "application/json"), 
                ("Content-Length", str(len(response_body)))
                 ]
                )
        
            return [response_body]

if __name__ == "__main__":
    app = ReviewAnalyzerServer()
    port = os.environ.get('PORT', 8000)
    with make_server("", port, app) as httpd:
        print(f"Listening on port {port}...")
        httpd.serve_forever()