"""
Azure Blob Storage Manager for EDISON PRO
Author: Srikanth Bhakthan - Microsoft

Provides blob storage integration for:
- Reading input files (PDFs, images) from Azure Blob Storage
- Writing analysis results and intermediate files to blob storage
- Streaming operations for efficiency
- Parallel upload/download operations
- Progress tracking for large operations

Usage:
    # Initialize manager
    blob_manager = BlobStorageManager(connection_string, container_name)
    
    # Download files for processing
    local_files = blob_manager.download_blobs_to_temp(prefix="drawings/")
    
    # Upload results
    blob_manager.upload_folder_to_blob("./intermediate_files", "results/analysis-123/")
"""

import os
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Callable
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import asyncio
import time

try:
    from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient, generate_blob_sas, BlobSasPermissions
    from azure.core.exceptions import ResourceNotFoundError, ResourceExistsError
    from azure.identity import DefaultAzureCredential
    HAS_AZURE_BLOB = True
except ImportError:
    print("⚠️  Warning: azure-storage-blob not available. Install with: pip install azure-storage-blob")
    HAS_AZURE_BLOB = False


class BlobStorageManager:
    """Manage Azure Blob Storage operations for EDISON PRO with optimizations"""
    
    def __init__(
        self, 
        connection_string: Optional[str] = None,
        container_name: Optional[str] = None,
        use_managed_identity: bool = False,
        account_url: Optional[str] = None
    ):
        """Initialize Blob Storage Manager.
        
        Args:
            connection_string: Azure Storage connection string
            container_name: Default container name
            use_managed_identity: Use managed identity instead of connection string
            account_url: Storage account URL (required if using managed identity)
        """
        if not HAS_AZURE_BLOB:
            raise ImportError("azure-storage-blob package is required. Install with: pip install azure-storage-blob")
        
        self.container_name = container_name
        self.use_managed_identity = use_managed_identity
        
        # Initialize blob service client
        if use_managed_identity:
            if not account_url:
                raise ValueError("account_url is required when using managed identity")
            credential = DefaultAzureCredential()
            self.blob_service_client = BlobServiceClient(account_url=account_url, credential=credential)
            print(f"✅ Blob Storage initialized with Managed Identity: {account_url}")
        else:
            if not connection_string:
                raise ValueError("connection_string is required when not using managed identity")
            self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
            # Extract account name for display
            account_name = connection_string.split("AccountName=")[1].split(";")[0] if "AccountName=" in connection_string else "unknown"
            print(f"✅ Blob Storage initialized: {account_name}")
        
        # Get container client if container specified
        self.container_client = None
        if container_name:
            self.container_client = self.blob_service_client.get_container_client(container_name)
            self._ensure_container_exists()
        
        # Temp directory for downloads
        self.temp_dir = None
    
    def _ensure_container_exists(self):
        """Ensure the container exists, create if it doesn't"""
        try:
            self.container_client.get_container_properties()
        except ResourceNotFoundError:
            print(f"📦 Container '{self.container_name}' not found, creating...")
            self.container_client.create_container()
            print(f"✅ Container '{self.container_name}' created successfully")
    
    def set_container(self, container_name: str):
        """Switch to a different container"""
        self.container_name = container_name
        self.container_client = self.blob_service_client.get_container_client(container_name)
        self._ensure_container_exists()
    
    def list_blobs(
        self, 
        prefix: str = "", 
        file_extensions: Optional[List[str]] = None,
        recursive: bool = True
    ) -> List[Dict[str, any]]:
        """List blobs in container matching criteria.
        
        Args:
            prefix: Blob name prefix filter (e.g., "drawings/2024/")
            file_extensions: List of extensions to filter (e.g., [".pdf", ".png"])
            recursive: Include all nested folders
            
        Returns:
            List of blob info dicts with name, size, last_modified, url
        """
        if not self.container_client:
            raise ValueError("Container not set. Call set_container() first.")
        
        print(f"📋 Listing blobs in container '{self.container_name}' with prefix '{prefix}'...")
        
        blobs = []
        blob_list = self.container_client.list_blobs(name_starts_with=prefix)
        
        for blob in blob_list:
            # Filter by extension if specified
            if file_extensions:
                if not any(blob.name.lower().endswith(ext.lower()) for ext in file_extensions):
                    continue
            
            # Skip directory markers (0-byte blobs ending with /)
            if blob.size == 0 and blob.name.endswith('/'):
                continue
            
            blob_info = {
                "name": blob.name,
                "size": blob.size,
                "last_modified": blob.last_modified,
                "url": f"{self.blob_service_client.url}/{self.container_name}/{blob.name}",
                "content_type": blob.content_settings.content_type if blob.content_settings else None
            }
            blobs.append(blob_info)
        
        print(f"   ✅ Found {len(blobs)} blob(s)")
        return blobs
    
    def download_blob_to_temp(self, blob_name: str) -> str:
        """Download a single blob to temporary directory.
        
        Args:
            blob_name: Name of blob to download
            
        Returns:
            Local file path where blob was downloaded
        """
        if not self.container_client:
            raise ValueError("Container not set. Call set_container() first.")
        
        # Create temp directory if needed
        if not self.temp_dir:
            self.temp_dir = tempfile.mkdtemp(prefix="edison_blob_")
        
        # Preserve directory structure in temp
        local_path = Path(self.temp_dir) / blob_name
        local_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Download blob
        blob_client = self.container_client.get_blob_client(blob_name)
        
        print(f"   ⬇️  Downloading: {blob_name}")
        start_time = time.time()
        
        with open(local_path, "wb") as file:
            download_stream = blob_client.download_blob()
            file.write(download_stream.readall())
        
        elapsed = time.time() - start_time
        size_mb = local_path.stat().st_size / (1024 * 1024)
        print(f"   ✅ Downloaded {size_mb:.2f} MB in {elapsed:.1f}s → {local_path}")
        
        return str(local_path)
    
    def download_blobs_to_temp(
        self, 
        prefix: str = "",
        file_extensions: Optional[List[str]] = None,
        max_workers: int = 4,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[str]:
        """Download multiple blobs to temporary directory in parallel.
        
        Args:
            prefix: Blob name prefix filter
            file_extensions: List of extensions to filter
            max_workers: Number of parallel downloads
            progress_callback: Optional callback(current, total) for progress tracking
            
        Returns:
            List of local file paths where blobs were downloaded
        """
        # Get list of blobs to download
        blobs = self.list_blobs(prefix=prefix, file_extensions=file_extensions)
        
        if not blobs:
            print(f"⚠️  No blobs found matching criteria")
            return []
        
        print(f"📥 Downloading {len(blobs)} blob(s) with {max_workers} parallel workers...")
        
        local_paths = []
        
        # Parallel download
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all download tasks
            future_to_blob = {
                executor.submit(self.download_blob_to_temp, blob['name']): blob 
                for blob in blobs
            }
            
            # Process completed downloads
            completed = 0
            for future in as_completed(future_to_blob):
                blob = future_to_blob[future]
                try:
                    local_path = future.result()
                    local_paths.append(local_path)
                    completed += 1
                    
                    # Progress callback
                    if progress_callback:
                        progress_callback(completed, len(blobs))
                    
                except Exception as e:
                    print(f"   ❌ Failed to download {blob['name']}: {e}")
        
        print(f"✅ Downloaded {len(local_paths)}/{len(blobs)} blob(s) successfully")
        return local_paths
    
    def upload_file_to_blob(
        self, 
        local_path: str, 
        blob_path: str,
        overwrite: bool = True,
        content_type: Optional[str] = None
    ) -> str:
        """Upload a single file to blob storage.
        
        Args:
            local_path: Local file path to upload
            blob_path: Destination blob path (name)
            overwrite: Overwrite if blob exists
            content_type: Optional content type (auto-detected if None)
            
        Returns:
            Blob URL
        """
        if not self.container_client:
            raise ValueError("Container not set. Call set_container() first.")
        
        local_file = Path(local_path)
        if not local_file.exists():
            raise FileNotFoundError(f"Local file not found: {local_path}")
        
        # Auto-detect content type if not provided
        if not content_type:
            content_type = self._detect_content_type(local_path)
        
        blob_client = self.container_client.get_blob_client(blob_path)
        
        print(f"   ⬆️  Uploading: {local_file.name} → {blob_path}")
        start_time = time.time()
        
        with open(local_path, "rb") as data:
            blob_client.upload_blob(
                data, 
                overwrite=overwrite,
                content_settings={"content_type": content_type} if content_type else None
            )
        
        elapsed = time.time() - start_time
        size_mb = local_file.stat().st_size / (1024 * 1024)
        blob_url = blob_client.url
        print(f"   ✅ Uploaded {size_mb:.2f} MB in {elapsed:.1f}s")
        
        return blob_url
    
    def upload_folder_to_blob(
        self, 
        local_folder: str, 
        blob_prefix: str,
        max_workers: int = 4,
        file_extensions: Optional[List[str]] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[str]:
        """Upload entire folder to blob storage in parallel.
        
        Args:
            local_folder: Local folder path to upload
            blob_prefix: Destination blob prefix (folder path in container)
            max_workers: Number of parallel uploads
            file_extensions: Optional list of extensions to filter
            progress_callback: Optional callback(current, total) for progress tracking
            
        Returns:
            List of blob URLs
        """
        local_path = Path(local_folder)
        if not local_path.exists():
            raise FileNotFoundError(f"Local folder not found: {local_folder}")
        
        # Get all files to upload
        all_files = []
        for file_path in local_path.rglob("*"):
            if file_path.is_file():
                # Filter by extension if specified
                if file_extensions and not any(str(file_path).lower().endswith(ext.lower()) for ext in file_extensions):
                    continue
                all_files.append(file_path)
        
        if not all_files:
            print(f"⚠️  No files found in {local_folder}")
            return []
        
        print(f"📤 Uploading {len(all_files)} file(s) from '{local_folder}' with {max_workers} parallel workers...")
        
        # Ensure blob_prefix ends with /
        if blob_prefix and not blob_prefix.endswith('/'):
            blob_prefix += '/'
        
        blob_urls = []
        
        # Parallel upload
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all upload tasks
            future_to_file = {}
            for file_path in all_files:
                # Calculate relative path for blob
                relative_path = file_path.relative_to(local_path)
                blob_path = f"{blob_prefix}{relative_path}".replace("\\", "/")  # Ensure forward slashes
                
                future = executor.submit(self.upload_file_to_blob, str(file_path), blob_path)
                future_to_file[future] = file_path
            
            # Process completed uploads
            completed = 0
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    blob_url = future.result()
                    blob_urls.append(blob_url)
                    completed += 1
                    
                    # Progress callback
                    if progress_callback:
                        progress_callback(completed, len(all_files))
                    
                except Exception as e:
                    print(f"   ❌ Failed to upload {file_path.name}: {e}")
        
        print(f"✅ Uploaded {len(blob_urls)}/{len(all_files)} file(s) successfully")
        return blob_urls
    
    def generate_sas_url(
        self, 
        blob_name: str, 
        expiry_hours: int = 24,
        permissions: str = "r"
    ) -> str:
        """Generate SAS URL for secure blob access.
        
        Args:
            blob_name: Name of blob
            expiry_hours: Hours until SAS token expires
            permissions: Permissions string (r=read, w=write, d=delete, l=list)
            
        Returns:
            SAS URL for blob access
        """
        if not self.container_client:
            raise ValueError("Container not set. Call set_container() first.")
        
        if self.use_managed_identity:
            print("⚠️  SAS URL generation not supported with Managed Identity")
            return f"{self.blob_service_client.url}/{self.container_name}/{blob_name}"
        
        blob_client = self.container_client.get_blob_client(blob_name)
        
        # Generate SAS token
        sas_token = generate_blob_sas(
            account_name=blob_client.account_name,
            container_name=self.container_name,
            blob_name=blob_name,
            account_key=blob_client.credential.account_key,
            permission=BlobSasPermissions(read='r' in permissions, write='w' in permissions),
            expiry=datetime.utcnow() + timedelta(hours=expiry_hours)
        )
        
        sas_url = f"{blob_client.url}?{sas_token}"
        print(f"🔗 Generated SAS URL (expires in {expiry_hours}h): {blob_name}")
        return sas_url
    
    def stream_download_to_memory(self, blob_name: str) -> bytes:
        """Download blob directly to memory (for small files).
        
        Args:
            blob_name: Name of blob to download
            
        Returns:
            Blob content as bytes
        """
        if not self.container_client:
            raise ValueError("Container not set. Call set_container() first.")
        
        blob_client = self.container_client.get_blob_client(blob_name)
        download_stream = blob_client.download_blob()
        return download_stream.readall()
    
    def stream_upload_from_memory(
        self, 
        data: bytes, 
        blob_path: str,
        content_type: Optional[str] = None
    ) -> str:
        """Upload data directly from memory to blob.
        
        Args:
            data: Bytes to upload
            blob_path: Destination blob path
            content_type: Optional content type
            
        Returns:
            Blob URL
        """
        if not self.container_client:
            raise ValueError("Container not set. Call set_container() first.")
        
        blob_client = self.container_client.get_blob_client(blob_path)
        blob_client.upload_blob(
            data,
            overwrite=True,
            content_settings={"content_type": content_type} if content_type else None
        )
        
        return blob_client.url
    
    def cleanup_temp_files(self):
        """Delete temporary download directory"""
        if self.temp_dir and Path(self.temp_dir).exists():
            print(f"🧹 Cleaning up temporary files: {self.temp_dir}")
            shutil.rmtree(self.temp_dir)
            self.temp_dir = None
    
    def _detect_content_type(self, file_path: str) -> str:
        """Detect content type from file extension"""
        ext = Path(file_path).suffix.lower()
        content_types = {
            '.pdf': 'application/pdf',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp',
            '.tiff': 'image/tiff',
            '.tif': 'image/tiff',
            '.json': 'application/json',
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.html': 'text/html',
            '.xml': 'application/xml',
            '.csv': 'text/csv'
        }
        return content_types.get(ext, 'application/octet-stream')
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup temp files"""
        self.cleanup_temp_files()


# Helper function for easy initialization from environment variables
def create_blob_manager_from_env(
    container_name: Optional[str] = None,
    env_prefix: str = "AZURE_STORAGE"
) -> Optional[BlobStorageManager]:
    """Create BlobStorageManager from environment variables.
    
    Args:
        container_name: Container name (overrides env var)
        env_prefix: Prefix for env variables (default: AZURE_STORAGE)
        
    Environment Variables:
        AZURE_STORAGE_CONNECTION_STRING: Connection string
        AZURE_STORAGE_ACCOUNT_URL: Storage account URL (for managed identity)
        AZURE_STORAGE_USE_MANAGED_IDENTITY: "true" to use managed identity
        AZURE_STORAGE_CONTAINER_NAME: Default container name
        
    Returns:
        BlobStorageManager instance or None if not configured
    """
    connection_string = os.getenv(f"{env_prefix}_CONNECTION_STRING")
    account_url = os.getenv(f"{env_prefix}_ACCOUNT_URL")
    use_managed_identity = os.getenv(f"{env_prefix}_USE_MANAGED_IDENTITY", "").lower() == "true"
    container = container_name or os.getenv(f"{env_prefix}_CONTAINER_NAME")
    
    # Check if blob storage is configured
    if not connection_string and not (use_managed_identity and account_url):
        return None
    
    try:
        return BlobStorageManager(
            connection_string=connection_string,
            container_name=container,
            use_managed_identity=use_managed_identity,
            account_url=account_url
        )
    except Exception as e:
        print(f"⚠️  Failed to initialize blob storage: {e}")
        return None
