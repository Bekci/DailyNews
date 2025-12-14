from dotenv import load_dotenv
load_dotenv()
import kaggle

DATASET_SLUG = "burakbekci/dailynewsinferencecode"
NOTEBOOK_SLUG = "burakbekci/xtts-inference"

class KaggleAPI:
    def __init__(self, dataset_path: str, notebook_path: str):
        self.dataset_path = dataset_path
        self.notebook_path = notebook_path
        kaggle.api.authenticate()

    def download_dataset(self):
        kaggle.api.dataset_download_files(DATASET_SLUG, path=self.dataset_path, quiet=False, unzip=True)

    def upload_dataset(self, dataset_path: str):
        kaggle.api.dataset_create_version(dataset_path, version_notes="Daily update", delete_old_versions=True)

    def download_notebook(self):
        kaggle.api.kernels_pull(NOTEBOOK_SLUG, path=self.notebook_path, metadata=False, quiet=False)

    def upload_notebook(self):
        kaggle.api.kernels_push(self.notebook_path)
