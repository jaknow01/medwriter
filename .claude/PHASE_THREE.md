# PHASE THREE of Development

1. Create FastAPI in the backend that can connect to Postgres database and Redis.
2. Create the UI and connect FastAPI to it. There should be a welcomming page where you can choose whether you want to continue writing process or create a new draft. If the User chooses to continue the conversation there should be a list of previous conversations to choose from. If a user chooses a converastion or clicks "new draft" on the previous page there should be a chat-like page to actually interact with the backend. NOTE - The UI must be entirely in polish - the user is polih and doesn't know amy other languages.
3. After a message is typed in and sent the FastAPI should be able to create a job in redis and then listen for status changes.
4. The job can be picked up by the singluar worker, processed and then return to redis as ready. FastAPI should be able to pick up on the task being finished, fetch data from redis, clear the job and display the response in the UI.
5. Test out the functionalities by running a sample work load and doing unit tests.