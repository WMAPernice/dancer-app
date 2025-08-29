# Conda Environment Setup for DANCER Backend

This guide provides multiple ways to set up the DANCER backend using conda environments.

## Option 1: Using environment.yml (Recommended)

### Quick Setup
```bash
# Navigate to backend directory
cd backend

# Create environment from yml file
conda env create -f environment.yml

# Activate environment
conda activate dancer-backend

# Verify installation
python -c "import fastapi, boto3, sqlalchemy; print('All packages installed successfully!')"
```

### Manual Environment Management
```bash
# Update existing environment
conda env update -f environment.yml

# Remove environment
conda env remove -n dancer-backend

# Export current environment
conda env export > environment-backup.yml
```

## Option 2: Using requirements.txt with conda

### Create Environment and Install with pip
```bash
# Create conda environment with Python
conda create -n dancer-backend python=3.9

# Activate environment
conda activate dancer-backend

# Install packages using pip
pip install -r requirements.txt
```

## Option 3: Manual conda installation

### Step-by-step conda package installation
```bash
# Create environment
conda create -n dancer-backend python=3.9

# Activate environment
conda activate dancer-backend

# Install available packages via conda
conda install -c conda-forge sqlalchemy python-dotenv

# Install remaining packages via pip
pip install fastapi==0.104.1 uvicorn[standard]==0.24.0 python-multipart==0.0.6 boto3==1.34.0 pydantic==2.5.0
```

## Package Availability in Conda

### ✅ Available via conda-forge:
- `python` - Base Python interpreter
- `sqlalchemy` - Database ORM
- `python-dotenv` - Environment variable management
- `pip` - Python package installer

### ⚠️ Better via pip:
- `fastapi` - Modern web framework (more up-to-date on PyPI)
- `uvicorn` - ASGI server (with [standard] extras)
- `pydantic` - Data validation (more up-to-date on PyPI)
- `boto3` - AWS SDK (more up-to-date on PyPI)
- `python-multipart` - Multipart form parsing

## Environment Management Commands

### Activation/Deactivation
```bash
# Activate environment
conda activate dancer-backend

# Deactivate environment
conda deactivate
```

### Environment Info
```bash
# List all environments
conda env list

# Show packages in current environment
conda list

# Show packages installed via pip
pip list
```

### Updating Packages
```bash
# Update conda packages
conda update sqlalchemy python-dotenv

# Update pip packages
pip install --upgrade fastapi uvicorn boto3 pydantic python-multipart
```

## Development Workflow

### Daily Usage
```bash
# Start development session
conda activate dancer-backend
cd backend

# Run the server
python start.py

# Or directly with uvicorn
uvicorn main:app --reload
```

### Sharing Environment
```bash
# Export exact environment (includes all dependencies)
conda env export > environment-full.yml

# Export only manually installed packages
conda env export --from-history > environment-minimal.yml

# Share with collaborators
git add environment.yml
git commit -m "Add conda environment file"
```

## Troubleshooting

### Common Issues

1. **Package conflicts**
   ```bash
   # Clean conda cache
   conda clean --all
   
   # Recreate environment
   conda env remove -n dancer-backend
   conda env create -f environment.yml
   ```

2. **Mixed package managers**
   ```bash
   # Check what's installed via conda vs pip
   conda list
   
   # Reinstall problematic packages
   pip uninstall package-name
   conda install -c conda-forge package-name
   ```

3. **Version conflicts**
   ```bash
   # Create environment with specific Python version
   conda create -n dancer-backend python=3.9.18
   ```

### Performance Tips

- **Use conda-forge channel**: Generally more up-to-date packages
- **Pin Python version**: Avoid unexpected updates
- **Prefer conda for system dependencies**: Better integration with system libraries
- **Use pip for Python-specific packages**: Often more recent versions

## CI/CD Integration

### GitHub Actions Example
```yaml
- name: Set up Conda
  uses: conda-incubator/setup-miniconda@v2
  with:
    environment-file: backend/environment.yml
    activate-environment: dancer-backend

- name: Test installation
  run: |
    conda activate dancer-backend
    python -c "import fastapi, boto3, sqlalchemy"
```

### Docker Integration
```dockerfile
FROM continuumio/miniconda3

COPY backend/environment.yml /tmp/environment.yml
RUN conda env create -f /tmp/environment.yml

SHELL ["conda", "run", "-n", "dancer-backend", "/bin/bash", "-c"]
```

## Recommended Workflow for Collaborators

1. **Clone repository**
2. **Choose setup method**: environment.yml (recommended) or requirements.txt
3. **Create environment**: `conda env create -f environment.yml`
4. **Activate environment**: `conda activate dancer-backend`
5. **Configure AWS credentials**: Copy and edit `.env` file
6. **Run server**: `python start.py`

This approach ensures consistent environments across different machines and operating systems!
