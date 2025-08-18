# Server Manager API

This project is a simple "Server Manager" API built with Django REST Framework and Docker. It provides endpoints to manage server records and their assignment to available devices, simulating a core piece of a backend infrastructure management system.

This project was created as a take-home assignment for the Homerun Systems Intern position.

---

## Prerequisites

Before you begin, ensure you have the following installed:
* [Docker](https://docs.docker.com/get-docker/)
* [Docker Compose](https://docs.docker.com/compose/install/)

---

## Setup & Running

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/gagefulwood/homerun_project.git](https://github.com/gagefulwood/homerun_project.git)
    ```

2.  **Navigate to the project directory:**
    ```bash
    cd homerun_project
    ```

3.  **Build and run the services using Docker Compose:**
    ```bash
    docker-compose up --build
    ```
    This command will build the Docker image for the Django application, start the web service and a PostgreSQL database service, and apply the necessary database migrations.

4.  **Access the API:**
    The API will be running and available at `http://localhost:8000/api/`. You can access the browsable API by opening that URL in your web browser.

---

## Quick Usage Example

You can interact with the API using any HTTP client, such as `curl` or Postman.

1.  **Create a Device:**
    ```bash
    curl -X POST http://localhost:8000/api/devices/ \
    -H "Content-Type: application/json" \
    -d '{"name": "Edge-Node-123"}'
    ```

2.  **Create a Server:**
    ```bash
    curl -X POST http://localhost:8000/api/servers/ \
    -H "Content-Type: application/json" \
    -d '{"name": "My Minecraft Server"}'
    ```

3.  **Start the Server (assuming the new server has an ID of 1):**
    ```bash
    curl -X PATCH http://localhost:8000/api/servers/1/ \
    -H "Content-Type: application/json" \
    -d '{"status": "starting"}'
    ```
    The API will automatically assign the server to the `Edge-Node-123` device and update its status to `running`.

---

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

Please make sure to update tests as appropriate.

---

## License

This project is licensed under the MIT License.
