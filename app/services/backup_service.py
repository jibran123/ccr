"""
Backup and restore service for MongoDB.

Handles backup creation, restoration, and management with
pluggable storage backends (local volume, S3, etc.).
"""

import logging
import os
import shutil
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path
import gzip
import json

from pymongo import MongoClient
from bson import json_util

logger = logging.getLogger(__name__)


class BackupService:
    """Service for managing MongoDB backups."""
    
    def __init__(self, mongo_uri: str, db_name: str, backup_dir: str):
        """
        Initialize backup service.
        
        Args:
            mongo_uri: MongoDB connection URI
            db_name: Database name to backup
            backup_dir: Directory to store backups
        """
        self.mongo_uri = mongo_uri
        self.db_name = db_name
        self.backup_dir = Path(backup_dir)
        
        # Ensure backup directory exists
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"BackupService initialized: db={db_name}, backup_dir={backup_dir}")
    
    def create_backup(self, compression: bool = True) -> Dict[str, Any]:
        """
        Create a full database backup.
        
        Args:
            compression: Whether to compress backup (gzip)
            
        Returns:
            Dictionary with backup metadata
            
        Raises:
            Exception: If backup fails
        """
        timestamp = datetime.utcnow()
        timestamp_str = timestamp.strftime('%Y%m%d_%H%M%S')
        
        # Create backup filename
        if compression:
            backup_filename = f"backup_{self.db_name}_{timestamp_str}.json.gz"
        else:
            backup_filename = f"backup_{self.db_name}_{timestamp_str}.json"
        
        backup_path = self.backup_dir / backup_filename
        
        logger.info(f"Starting backup: {backup_filename}")
        
        try:
            # Connect to MongoDB
            client = MongoClient(self.mongo_uri)
            db = client[self.db_name]
            
            # Get all collections
            collections = db.list_collection_names()
            
            if not collections:
                logger.warning(f"Database '{self.db_name}' has no collections")
            
            # Backup data structure
            backup_data = {
                'metadata': {
                    'database': self.db_name,
                    'timestamp': timestamp.isoformat() + 'Z',
                    'collections': collections,
                    'compression': compression
                },
                'collections': {}
            }
            
            # Backup each collection
            total_documents = 0
            for collection_name in collections:
                collection = db[collection_name]
                documents = list(collection.find())
                
                backup_data['collections'][collection_name] = documents
                total_documents += len(documents)
                
                logger.info(f"  Backed up collection '{collection_name}': {len(documents)} documents")
            
            # Serialize to JSON
            json_data = json_util.dumps(backup_data, indent=2)
            
            # Write to file (compressed or not)
            if compression:
                with gzip.open(backup_path, 'wt', encoding='utf-8') as f:
                    f.write(json_data)
            else:
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(json_data)
            
            # Get file size
            file_size = backup_path.stat().st_size
            file_size_mb = file_size / (1024 * 1024)
            
            logger.info(f"✅ Backup completed: {backup_filename} ({file_size_mb:.2f} MB)")
            
            # Return metadata
            return {
                'success': True,
                'backup_id': timestamp_str,
                'filename': backup_filename,
                'path': str(backup_path),
                'size_bytes': file_size,
                'size_mb': round(file_size_mb, 2),
                'timestamp': timestamp.isoformat() + 'Z',
                'database': self.db_name,
                'collections': len(collections),
                'total_documents': total_documents,
                'compressed': compression
            }
            
        except Exception as e:
            logger.error(f"❌ Backup failed: {str(e)}", exc_info=True)
            
            # Clean up partial backup if exists
            if backup_path.exists():
                backup_path.unlink()
                logger.info(f"Cleaned up partial backup: {backup_filename}")
            
            raise Exception(f"Backup failed: {str(e)}")
        
        finally:
            client.close()
    
    def restore_backup(self, backup_id: str, drop_existing: bool = False) -> Dict[str, Any]:
        """
        Restore database from backup.
        
        Args:
            backup_id: Backup timestamp ID (e.g., '20251030_020000')
            drop_existing: Whether to drop existing collections before restore
            
        Returns:
            Dictionary with restore metadata
            
        Raises:
            Exception: If restore fails
        """
        logger.info(f"Starting restore from backup: {backup_id}")
        
        # Find backup file (try compressed first, then uncompressed)
        backup_filename_gz = f"backup_{self.db_name}_{backup_id}.json.gz"
        backup_filename = f"backup_{self.db_name}_{backup_id}.json"
        
        backup_path_gz = self.backup_dir / backup_filename_gz
        backup_path = self.backup_dir / backup_filename
        
        if backup_path_gz.exists():
            backup_path = backup_path_gz
            compressed = True
        elif backup_path.exists():
            compressed = False
        else:
            raise FileNotFoundError(f"Backup not found: {backup_id}")
        
        logger.info(f"Found backup: {backup_path.name}")
        
        try:
            # Read backup file
            if compressed:
                with gzip.open(backup_path, 'rt', encoding='utf-8') as f:
                    json_data = f.read()
            else:
                with open(backup_path, 'r', encoding='utf-8') as f:
                    json_data = f.read()
            
            # Parse JSON
            backup_data = json_util.loads(json_data)
            
            # Validate backup structure
            if 'metadata' not in backup_data or 'collections' not in backup_data:
                raise ValueError("Invalid backup format")
            
            metadata = backup_data['metadata']
            collections_data = backup_data['collections']
            
            logger.info(f"Backup metadata: {metadata}")
            
            # Connect to MongoDB
            client = MongoClient(self.mongo_uri)
            db = client[self.db_name]
            
            # Drop existing collections if requested
            if drop_existing:
                logger.warning("Dropping existing collections...")
                for collection_name in db.list_collection_names():
                    db[collection_name].drop()
                    logger.info(f"  Dropped collection: {collection_name}")
            
            # Restore each collection
            total_restored = 0
            restored_collections = []
            
            for collection_name, documents in collections_data.items():
                collection = db[collection_name]
                
                if documents:
                    # Insert documents
                    result = collection.insert_many(documents)
                    count = len(result.inserted_ids)
                    total_restored += count
                    
                    logger.info(f"  Restored collection '{collection_name}': {count} documents")
                    restored_collections.append(collection_name)
                else:
                    logger.info(f"  Skipped empty collection: {collection_name}")
            
            logger.info(f"✅ Restore completed: {total_restored} documents across {len(restored_collections)} collections")
            
            return {
                'success': True,
                'backup_id': backup_id,
                'database': self.db_name,
                'collections_restored': len(restored_collections),
                'total_documents': total_restored,
                'drop_existing': drop_existing,
                'restored_at': datetime.utcnow().isoformat() + 'Z'
            }
            
        except Exception as e:
            logger.error(f"❌ Restore failed: {str(e)}", exc_info=True)
            raise Exception(f"Restore failed: {str(e)}")
        
        finally:
            client.close()
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """
        List all available backups.
        
        Returns:
            List of backup metadata dictionaries
        """
        backups = []
        
        # Find all backup files
        for backup_file in self.backup_dir.glob(f"backup_{self.db_name}_*.json*"):
            try:
                # Extract timestamp from filename
                # Format: backup_dbname_YYYYMMDD_HHMMSS.json[.gz]
                filename = backup_file.stem  # Remove .gz if present
                if filename.endswith('.json'):
                    filename = filename[:-5]  # Remove .json
                
                parts = filename.split('_')
                if len(parts) >= 3:
                    timestamp_str = f"{parts[-2]}_{parts[-1]}"
                    
                    # Parse timestamp
                    timestamp = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
                    
                    # Get file size
                    file_size = backup_file.stat().st_size
                    file_size_mb = file_size / (1024 * 1024)
                    
                    backups.append({
                        'backup_id': timestamp_str,
                        'filename': backup_file.name,
                        'path': str(backup_file),
                        'timestamp': timestamp.isoformat() + 'Z',
                        'size_bytes': file_size,
                        'size_mb': round(file_size_mb, 2),
                        'compressed': backup_file.suffix == '.gz',
                        'age_days': (datetime.utcnow() - timestamp).days
                    })
            except Exception as e:
                logger.warning(f"Could not parse backup file {backup_file.name}: {e}")
                continue
        
        # Sort by timestamp (newest first)
        backups.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return backups
    
    def delete_backup(self, backup_id: str) -> bool:
        """
        Delete a specific backup.
        
        Args:
            backup_id: Backup timestamp ID
            
        Returns:
            True if deleted successfully
            
        Raises:
            FileNotFoundError: If backup doesn't exist
        """
        # Find backup file
        backup_filename_gz = f"backup_{self.db_name}_{backup_id}.json.gz"
        backup_filename = f"backup_{self.db_name}_{backup_id}.json"
        
        backup_path_gz = self.backup_dir / backup_filename_gz
        backup_path = self.backup_dir / backup_filename
        
        if backup_path_gz.exists():
            backup_path_gz.unlink()
            logger.info(f"Deleted backup: {backup_filename_gz}")
            return True
        elif backup_path.exists():
            backup_path.unlink()
            logger.info(f"Deleted backup: {backup_filename}")
            return True
        else:
            raise FileNotFoundError(f"Backup not found: {backup_id}")
    
    def cleanup_old_backups(self, retention_days: int = 7) -> Dict[str, Any]:
        """
        Delete backups older than retention period.
        
        Args:
            retention_days: Keep backups newer than this many days
            
        Returns:
            Dictionary with cleanup results
        """
        logger.info(f"Cleaning up backups older than {retention_days} days...")
        
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        deleted_count = 0
        deleted_size = 0
        
        for backup in self.list_backups():
            backup_date = datetime.fromisoformat(backup['timestamp'].replace('Z', ''))
            
            if backup_date < cutoff_date:
                try:
                    self.delete_backup(backup['backup_id'])
                    deleted_count += 1
                    deleted_size += backup['size_bytes']
                    logger.info(f"  Deleted old backup: {backup['filename']}")
                except Exception as e:
                    logger.error(f"  Failed to delete {backup['filename']}: {e}")
        
        logger.info(f"✅ Cleanup completed: Deleted {deleted_count} old backups ({deleted_size / (1024*1024):.2f} MB)")
        
        return {
            'success': True,
            'deleted_count': deleted_count,
            'deleted_size_mb': round(deleted_size / (1024*1024), 2),
            'retention_days': retention_days
        }