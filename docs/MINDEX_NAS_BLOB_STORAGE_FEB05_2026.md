# MINDEX NAS Blob Storage Configuration - Feb 5, 2026

## Overview

MINDEX stores binary large objects (images, DNA sequences, research PDFs) on the Mycosoft NAS server. This document describes the configuration and mounting procedures for the MINDEX VM (192.168.0.189).

## NAS Server Details

- **NAS IP**: 192.168.0.105
- **Share Name**: mycosoft
- **Share Path**: \\192.168.0.105\mycosoft
- **MINDEX Subdirectory**: mindex/

## Directory Structure

`
/mnt/nas/mycosoft/mindex/
â”œâ”€â”€ images/
â”‚   â”œâ”€â”€ species/           # Species/taxon images
â”‚   â”‚   â”œâ”€â”€ by_id/         # Organized by taxon ID (000-999 subdirs)
â”‚   â”‚   â””â”€â”€ by_name/       # Organized by genus/species
â”‚   â””â”€â”€ observations/      # Individual observation photos
â”œâ”€â”€ sequences/
â”‚   â”œâ”€â”€ fasta/             # FASTA sequence files
â”‚   â””â”€â”€ genbank/           # GenBank format files
â”œâ”€â”€ research/
â”‚   â”œâ”€â”€ pdfs/              # Research paper PDFs (year/month subdirs)
â”‚   â””â”€â”€ supplementary/     # Supplementary data files
â”œâ”€â”€ compounds/
â”‚   â”œâ”€â”€ structures/        # 2D/3D structure images
â”‚   â””â”€â”€ spectra/           # Spectral data
â””â”€â”€ temp/                  # Temporary downloads
`

## Linux Mount Configuration (MINDEX VM)

### 1. Install Required Packages

`ash
sudo apt-get update
sudo apt-get install -y cifs-utils
`

### 2. Create Mount Point

`ash
sudo mkdir -p /mnt/nas/mycosoft/mindex
`

### 3. Create Credentials File

`ash
sudo nano /etc/samba/.nascreds
`

Add:
`
username=mycosoft
password=YOUR_NAS_PASSWORD
domain=WORKGROUP
`

Secure the file:
`ash
sudo chmod 600 /etc/samba/.nascreds
`

### 4. Add to /etc/fstab for Persistent Mount

`ash
sudo nano /etc/fstab
`

Add this line:
`
//192.168.0.105/mycosoft/mindex /mnt/nas/mycosoft/mindex cifs credentials=/etc/samba/.nascreds,uid=1000,gid=1000,iocharset=utf8,file_mode=0664,dir_mode=0775,vers=3.0,nofail 0 0
`

### 5. Mount the Share

`ash
sudo mount -a
`

### 6. Verify Mount

`ash
df -h /mnt/nas/mycosoft/mindex
ls -la /mnt/nas/mycosoft/mindex
`

## Docker Container Access

For MINDEX Docker containers to access NAS storage, use volume mount:

`yaml
# docker-compose.yml
services:
  mindex-api:
    image: mycosoft/mindex-api:latest
    volumes:
      - /mnt/nas/mycosoft/mindex:/data/blobs:rw
    environment:
      - BLOB_STORAGE_PATH=/data/blobs
`

## Environment Variables

Add to MINDEX application environment:

`ash
# Blob storage configuration
BLOB_STORAGE_PATH=/mnt/nas/mycosoft/mindex
BLOB_STORAGE_URL=http://192.168.0.189:8001/mindex/blobs

# NAS connection (for direct access)
NAS_HOST=192.168.0.105
NAS_SHARE=mycosoft
NAS_MINDEX_PATH=mindex
`

## Permissions

Ensure the MINDEX application user has read/write access:

`ash
# Check ownership
ls -la /mnt/nas/mycosoft/mindex

# Set ownership if needed (replace with actual user)
sudo chown -R mycosoft:mycosoft /mnt/nas/mycosoft/mindex

# Set permissions
sudo chmod -R 775 /mnt/nas/mycosoft/mindex
`

## Windows Access (for debugging)

From Windows machines, access via:
`
\\192.168.0.105\mycosoft\mindex
`

Or map as network drive:
`cmd
net use M: \\192.168.0.105\mycosoft\mindex /user:mycosoft PASSWORD /persistent:yes
`

## Troubleshooting

### Mount fails with "Permission denied"
- Verify credentials in /etc/samba/.nascreds
- Check NAS share permissions for the user
- Try mounting with explicit credentials: sudo mount -t cifs //192.168.0.105/mycosoft/mindex /mnt/nas/mycosoft/mindex -o username=mycosoft,password=PASSWORD

### Slow performance
- Ensure using SMB 3.0 (ers=3.0 in mount options)
- Check network connectivity between MINDEX VM and NAS
- Consider using cache=loose mount option for read-heavy workloads

### Permission issues writing files
- Check ile_mode and dir_mode mount options
- Verify uid and gid match the application user
- Check NAS-side permissions

## Backup Considerations

The NAS should have:
- Regular backups of the mindex directory
- RAID configuration for redundancy
- Sufficient storage capacity (recommended: 2TB+ for full MINDEX dataset)

## Capacity Planning

Estimated storage requirements:
- Species images: ~500GB (5 images/species Ã— 575,000 species Ã— 200KB avg)
- DNA sequences: ~50GB (FASTA files)
- Research PDFs: ~100GB (100,000 papers Ã— 1MB avg)
- Compounds: ~10GB (structures and spectra)
- **Total estimated: ~700GB - 1TB**
