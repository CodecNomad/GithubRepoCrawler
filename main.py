import concurrent.futures
import os
import zipfile
from io import BytesIO
from typing import List, Optional

import requests


class GitHubAPI:
    """
    A class for interacting with GitHub repositories and scraping code files.
    """

    BASE_URL = "https://api.github.com"

    def __init__(self, repository_owner: str, repository_name: str, allowed_extensions: Optional[List[str]] = None):
        """
        Initialize a GitHubAPI instance.

        :param repository_owner: The owner of the GitHub repository.
        :param repository_name: The name of the GitHub repository.
        :param allowed_extensions: List of allowed file extensions to scrape (default is ['.md']).
        """
        self.owner = repository_owner
        self.repo = repository_name
        self.session = requests.Session()
        if allowed_extensions is None:
            self.allowed_extensions = [".md"]
        else:
            self.allowed_extensions = allowed_extensions

    def _make_request(self, url: str) -> requests.Response:
        """
        Make a GET request to the specified URL.

        :param url: The URL to make the request to.
        :return: The HTTP response object.
        """
        response = self.session.get(url)
        response.raise_for_status()
        return response

    def get_archive_url(self) -> str:
        """
        Get the URL to download the repository archive.

        :return: The archive download URL.
        """
        url = f"{self.BASE_URL}/repos/{self.owner}/{self.repo}/zipball/main"
        response = self._make_request(url)

        if response.status_code == 302:
            redirect_url = response.headers['Location']
            return redirect_url
        else:
            return url

    def get_all_file_paths(self) -> List[str]:
        """
        Get a list of all file paths in the repository archive.

        :return: List of file paths.
        """
        archive_url = self.get_archive_url()
        response = self._make_request(archive_url)

        with zipfile.ZipFile(BytesIO(response.content)) as zip_file:
            return [file_info.filename for file_info in zip_file.infolist()]

    def _scrape_code_for_file(self, path: str) -> str:
        """
        Scrape code from a single file in the repository.

        :param path: The file path to scrape.
        :return: A string containing the scraped code.
        """
        try:
            path_parts = path.split("/")
            path_parts.pop(0)
            file_name = path_parts[-1]

            # Check if the file extension is allowed
            if not any(file_name.endswith(ext) for ext in self.allowed_extensions):
                return ""

            url = f"https://raw.githubusercontent.com/{self.owner}/{self.repo}/main/{'/'.join(path_parts)}"
            response = requests.get(url)
            response.raise_for_status()

            buffer = f"\n\"{url}\" starts here\n{response.text}\n\"{file_name}\" ends here\n"
            return buffer
        except requests.exceptions.RequestException:
            return ""

    def scrape_code(self) -> str:
        """
        Scrape code from files in the repository using parallel processing.

        :return: A string containing scraped code snippets.
        """
        code_buffer = ""
        file_paths = self.get_all_file_paths()

        # Use concurrent.futures to parallelize the scraping process
        with concurrent.futures.ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
            code_futures = [executor.submit(self._scrape_code_for_file, path) for path in file_paths]

            for future in concurrent.futures.as_completed(code_futures):
                code_buffer += future.result()

        return code_buffer


# Example usage
import time

owner = "Shell1010"
repo = "Selfcord"

try:
    git = GitHubAPI(owner, repo)
    start_time = time.time()
    code = git.scrape_code()
    print(f"Scraping took {time.time() - start_time:.3f}s")
    with open("scraped.txt", "w") as file:
        file.write(code)
except Exception as e:
    print(f"An error occurred: {str(e)}")
