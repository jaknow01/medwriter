# PHASE TWO of Development

1. Create a Postgres database with all necessary tables: Convesations - conv_id (PK), creation_timestamp, some_kind_of_title; Messages - mess_id (PK), conv_id (FK), role (User/AI), content, timestamp
2. Worker can connect to the database. It can upload and download conversation data from there. Previous messages are appended to the query as context.
3. If the conversation doesn't have a title in the database it should be generated with LLM. This action is completely separate from the agent and it's a simple LLM API call. It's metadata are not saved anywhere. Only the title is saved to the database - it should be very short yet descriptive. If title already exists this part is skipped entirely
4. Create a Redis container. Worker can asynchronously look up data in redis and modify data in there.
5. Test out connections with sample workloads. Test new functions with unit testing.

Make sure to provide extensive logging to facilitate debugging. Agent should be independent of any particular LLM meaning that I should be able to switch providers seamlessly (only adding an appropriate API key to .env)