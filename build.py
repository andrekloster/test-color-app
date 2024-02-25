"""
This script automates the process of version bumping, Docker image building, pushing to a registry, and cleanup for a given project.
It leverages environment variables for configuration and supports the following key operations:

1. Version Bumping: Utilizes the `bump-my-version` command to increment the project's version in a TOML configuration file.
2. Current Version Retrieval: Reads the updated version from the TOML configuration file to tag the Docker image accordingly.
3. Docker Registry Login: Logs into a specified Docker registry using credentials provided through environment variables.
4. Docker Image Building: Builds a Docker image from a specified directory containing a Dockerfile and tags it with the current project version.
5. Docker Image Pushing: Pushes the tagged Docker image to the specified Docker registry.
6. Docker Image Cleanup: Removes the built Docker image from the local system and prunes any dangling images.

Environment variables are used to specify the project name, Docker registry credentials, 
and the path to the version file among other configurations. The script ensures that all necessary configurations are present
before proceeding with the operations. In case of missing configurations or errors during any of the operations, 
the script will terminate with an appropriate error message.

Designed to be executed as part of a CI/CD pipeline or in development environments for automated Docker image management.

Dependencies:
- Docker Python SDK: For interacting with Docker.
- Python `subprocess`: For executing the version bump command.
- `toml` Python package: For parsing and reading the TOML configuration file.
- `python-dotenv`: For loading environment variables from a `.env` file.

Usage:
Ensure all required environment variables are set or defined in a `.env` file at the root of the project.
Then, run the script directly with Python to execute the defined workflow.
"""


import docker
import os
import subprocess
import sys
import toml
from dotenv import load_dotenv


# Function to get and return a Docker client instance from the environment.
def get_docker_client():
    """Create and return a Docker client instance based on environment configuration."""
    return docker.from_env()


# Function to bump the project version using the `bump-my-version` command.
def bump_version():
    """Run the `bump-my-version` command to bump the project's version."""
    command = ["bump-my-version", "bump", "patch"]
    subprocess.run(command)


# Function to read the current project version from a TOML configuration file.
def get_current_version(version_file):
    """Read and return the current project version from the specified TOML file."""
    with open(version_file, 'r') as toml_file:
        parsed_toml = toml.load(toml_file)
    return parsed_toml["tool"]["bumpversion"]["current_version"]


# Function to log in to a Docker registry using provided credentials.
def docker_login(client, username, password, registry):
    """Attempt to log in to the Docker registry using provided credentials.

    Args:
        client: Docker client instance.
        username: Username for the registry.
        password: Password for the registry.
        registry: Registry URL.

    Returns:
        True if login was successful, False otherwise.
    """
    try:
        client.login(username=username, password=password, registry=registry)
        print("Successfully logged into container registry.")
        return True
    except docker.errors.APIError as e:
        print(f"An error occurred: {e}")
        return False


# Function to build a Docker image from a specified path and tag it.
def build_image(client, path, image_name):
    """Build a Docker image from the specified path and tag it.

    Args:
        client: Docker client instance.
        path: Path to the directory containing the Dockerfile.
        image_name: Name to tag the image with.
    """
    print(f"Building container image: {image_name}")
    [line for line in client.images.build(path=path, tag=image_name, rm=True)]
    print(f"Image {image_name} build successfully!")


# Function to push a Docker image to a registry.
def push_image(client, image_name):
    """Push a Docker image to a registry.

    Args:
        client: Docker client instance.
        image_name: Name of the image to push.
    """
    try:
        for line in client.images.push(image_name, stream=True, decode=True):
            print(line)
        print(f"Image {image_name} successfully pushed.")
    except docker.errors.APIError as e:
        print(f"An error occurred while pushing the image: {e}")


# Function to remove a Docker image from the local system.
def remove_image(client, image_name):
    """Remove a Docker image from the local system and prune any dangling images.

    Args:
        client: Docker client instance.
        image_name: Name of the image to remove.
    """
    try:
        client.images.remove(image=image_name)
        client.images.prune(filters={'dangling': True})
        print(f"Image {image_name} successfully removed.")
    except docker.errors.ImageNotFound:
        print(f"Image {image_name} not found.")
    except docker.errors.APIError as e:
        print(f"Error removing the image {image_name}: {e}")


def main():
    """Main function to orchestrate the version bumping, image building, pushing, and removal."""
    # Load environment variables from the .env file if they are not already defined in the system environment.
    load_dotenv()

    # Attempt to read the environment variables. If a variable is not set, None is returned
    # (alternatively, a default value could be specified here).
    version_file = os.getenv("VERSION_FILE")
    project_name = os.getenv("PROJECT_NAME")
    registry_username = os.getenv("REGISTRY_USERNAME")
    registry_password = os.getenv("REGISTRY_PASSWORD")
    registry_name = os.getenv("REGISTRY_NAME")

    # Check if all required environment variables are present
    required_vars = [version_file, project_name, registry_username, registry_password, registry_name]
    if any(var is None for var in required_vars):
        print("Some required environment variables are missing. Please ensure all needed variables are set.")
        sys.exit(1)

    # Perform the version bumping
    bump_version()

    # Retrieve the current version from the specified file
    current_version = get_current_version(version_file)
    print(f"Current version: {current_version}")

    # Construct the URL for the Docker registry
    registry_url = f"https://{registry_name}/"

    # Create an instance of the Docker client
    client = get_docker_client()

    # Attempt to log in to the Docker registry
    if not docker_login(client, registry_username, registry_password, registry_url):
        sys.exit(1)

    # Path to the Dockerfile and name of the image to be built
    path = "."
    image_name = f"{registry_name}/{project_name}:{current_version}"

    # Build the Docker image, push it, and then remove it afterwards
    build_image(client, path, image_name)
    push_image(client, image_name)
    remove_image(client, image_name)


if __name__ == "__main__":
    main()
