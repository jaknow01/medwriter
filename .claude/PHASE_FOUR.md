# PHASE FOUR of Development

1. Add additional workers that operate asynchronously (3 of them)
2. Add ability to add additional workers if the workload is very heavy (max 6 workers in total)
3. Make sure that the workers can access redis and postgres without any concurency issues. Apply necessary locks where needed.
4. Make sure that the UI can support multiple conversations at once (start with 2).
5. Make sure that API can support multiple conversations going on at once in the UI and still maintain its functionalities
6. Test out the system by running a sample workload