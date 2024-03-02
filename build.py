import argparse
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
def bump_version(version_file):
    """Run the `bump-my-version` command to bump the project's version."""
    command = ["bump-my-version", "bump", "patch", "--config-file", f"{version_file}", "--allow-dirty"]
    subprocess.run(command)


# Function to read the current project version from a TOML configuration file.
def get_current_version(version, is_production=True):
    if is_production:
        """Read and return the current project version from the specified TOML file."""
        with open(version, 'r') as toml_file:
            parsed_toml = toml.load(toml_file)
        return parsed_toml["tool"]["bumpversion"]["current_version"]
    
    return version


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
def build_image(client, build_path, image_name):
    """Build a Docker image from the specified path and tag it.

    Args:
        client: Docker client instance.
        path: Path to the directory containing the Dockerfile.
        image_name: Name to tag the image with.
    """
    print(f"Building container image: {image_name}")
    [line for line in client.images.build(path=build_path, tag=image_name, rm=True)]
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

    parser = argparse.ArgumentParser()
    parser.add_argument('-e', '--environment', type=str, default='production', required=True, help='deployment environment')
    parser.add_argument('-v', '--version', type=str, default=None, nargs='?', help='version as string')
    args = parser.parse_args()

    if args.version is not None and not args.environment == 'production':
        version = args.version
    else:
        version = os.getenv("VERSION")
    # Attempt to read the environment variables. If a variable is not set, None is returned
    # (alternatively, a default value could be specified here).
    project_name = os.getenv("PROJECT_NAME")
    registry_username = os.getenv("REGISTRY_USERNAME")
    registry_password = os.getenv("REGISTRY_PASSWORD")
    registry_name = os.getenv("REGISTRY_NAME")

    # Check if all required environment variables are present
    required_vars = [version, project_name, registry_username, registry_password, registry_name]
    if any(var is None for var in required_vars):
        print("Some required environment variables are missing. Please ensure all needed variables are set.")
        sys.exit(1)

    # Retrieve the current version from the specified file
    if args.environment == 'production':
        current_version = get_current_version(version)
        # Perform the version bumping
        bump_version(version)
    else:
        current_version = get_current_version(version, is_production=False)
    print(f"Current version: {current_version}")

    # Construct the URL for the Docker registry
    registry_url = f"https://{registry_name}/"

    # Create an instance of the Docker client
    client = get_docker_client()

    # Attempt to log in to the Docker registry
    if not docker_login(client, registry_username, registry_password, registry_url):
        sys.exit(1)

    # Path to the Dockerfile and name of the image to be built
    build_path = "."
    image_name = f"{registry_name}/{project_name}:{current_version}"

    # Build the Docker image, push it, and then remove it afterwards
    build_image(client, build_path, image_name)
    push_image(client, image_name)
    remove_image(client, image_name)


if __name__ == "__main__":
    main()

