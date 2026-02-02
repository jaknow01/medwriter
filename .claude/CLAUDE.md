# PROJECT OVERVIEW

## General purpose
This project is a interactive tool for drafting articles on medical subjects. The goal is to allow a few users to quickly create articles which can be later verified by real-life doctors so that they can be posted on the company's website. The tool comes equipped with an intuitive UI and allows a limited number of user's to work at the same time. Previous exchanges with the tool are saved and can be accessed later by anyone with the access to the UI. 

## Technical details
Under the hood there is an Agent (written in Llamaindex) that uses its MCP Client to connect to MCP server via HTTP. The server is a separate project, here we focus on the engine (agent), MCP client, UI and how they interact with each other. The project also assumes that there is a Postgres database in where all information about messages and conversations is being stored. 

The full flow of a finished MVP would be ass follows:
1. The Users enter a given URL where the UI has been created.
2. The Users can either start a new conversation or select one of the previous ones - there is no need for authentication and authorization, all users can see all previous convos of other users
3. There is a FastAPI communication layer between the front and backend. It can also communicate with Postgres database where details of all previous conversations are stored. Each conversation has its own unique ID.
4. If the user chooses an existing conversation the API retrieves all information about it from the database which allows the UI to rebuild it, show it to the User and allow him to continue that given conversation
5. If the user starts a new conversation API creates a new record in the Conversations table in the database and a new record in the Messages table. Then it sends a job to redis. The job contains conversation_id, user's query, status=Pending, result=Pending
6. The actual work of analyzing the query is done by workers. There are 3 workers on stand by but more can be dynamically created if the workload is big (max 6 workers in total to preserve LLM API tokens). The workers run asynchronously and independent of each other. Each worker consits of an Agent engine (LLM selection, system prompt, etc) and an MCP Client.
7. Each worker is constantly checking if there are jobs in redis that have "Pending" status. If one appears then the first worker to see it takes this job for processing. The status of a job is changed to "Processing" and the worker starts its task. WARNING - There have to be appropriate lock mechanisms in place to make sure that exactly one worker performs a given job and to avoid concurrency issues.
8. The worker first checks if this conversation is a new one or if there have been some previous messages in the Postgres database. If this is part of an existing conversation then the worker downloads previous messages and attaches them to the query as context. 
9. The worker starts connection with MCP Servers where actually tools will be run. The MCP Server first returns a list of tools for the agent to choose from. Then the worker.
10. The worker decides which tools to use and the Server returns their results.
11. Once the worker generates his response based on the query and tool results it uploads the response message to the database.
12. The worker updates the job in redis. The job with a given conversation_id has its status changed to "Ready" and result to the agents response.
13. During all this time the FastAPI constantly checks what are the states of the jobs in redis. Once it finds a job with status "Ready" it gets that job's result and sends it to appropriate convesation in the UI.

All components should be contenerized: the frontend, redis, the backend (with workers and API). For maximum scalability the Postgres database should be in a separate container so that it is independent of the backend. It should be able to build the database on a separate device so that the engine with UI can work anywhere and you just point it to the location of the database. For the sake of development the database must be on the same device but keep the communication and build process separate the way it would work in real-life application (Postgres built with separate commands and communication via web protocols). 

The MCP Client should be written using FastMCP framework. For the sake of development you can create a dummy MCP Server that will be used for testing but keep the HTTP communication.

## Building process

The build process is divided into phases. Until the previous one is fully operational you cannot proceed to the next one. The phases are detailed in .claude/PHASE_*.md files.
