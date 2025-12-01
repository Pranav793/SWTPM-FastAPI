# TPM2 Documentation Guide

## Official Documentation Sources

### 1. **TPM2-Tools Documentation** (Command Line Tools)
- **ReadTheDocs**: https://tpm2-tools.readthedocs.io/en/latest/
- **GitHub Repository**: https://github.com/tpm2-software/tpm2-tools
- **Man Pages**: Available online and in the container

### 2. **TPM2-TSS Documentation** (Software Stack)
- **ReadTheDocs**: https://tpm2-tss.readthedocs.io/en/latest/
- **GitHub Repository**: https://github.com/tpm2-software/tpm2-tss
- **API Documentation**: https://tpm2-tss.readthedocs.io/en/latest/api/

### 3. **TPM2-ABRMD Documentation** (Access Broker)
- **GitHub Repository**: https://github.com/tpm2-software/tpm2-abrmd
- **Man Pages**: Available in the container

### 4. **SWTPM Documentation** (Software TPM Emulator)
- **GitHub Repository**: https://github.com/stefanberger/swtpm
- **Documentation**: https://github.com/stefanberger/swtpm/blob/master/README.md

## Key Documentation Sections

### TPM2-Tools (Command Line Interface)

#### Getting Started
- **Installation Guide**: https://tpm2-tools.readthedocs.io/en/latest/INSTALL/
- **Quick Start**: https://tpm2-tools.readthedocs.io/en/latest/quickstart/

#### Command Reference
- **All Commands**: https://tpm2-tools.readthedocs.io/en/latest/man/
- **Common Commands**:
  - `tpm2_createprimary`: Create primary keys
  - `tpm2_create`: Create keys
  - `tpm2_load`: Load keys into TPM
  - `tpm2_evictcontrol`: Make keys persistent
  - `tpm2_flushcontext`: Clear TPM contexts

#### Configuration
- **TCTI Configuration**: https://tpm2-tools.readthedocs.io/en/latest/man/common/tcti.md
- **Environment Variables**: TSS2_TCTI, TPM2TOOLS_TCTI

### TPM2-TSS (Software Stack)

#### API Documentation
- **ESAPI (Enhanced System API)**: https://tpm2-tss.readthedocs.io/en/latest/api/group__sapi.html
- **SAPI (System API)**: https://tpm2-tss.readthedocs.io/en/latest/api/group__sapi.html
- **FAPI (Feature API)**: https://tpm2-tss.readthedocs.io/en/latest/api/group__fapi.html

#### TCTI Documentation
- **TCTI Overview**: https://tpm2-tss.readthedocs.io/en/latest/tcti/
- **Available TCTIs**: device, tabrmd, swtpm, mssim

## TCG Specifications (Advanced)

### Core Specifications
- **TPM 2.0 Library Specification**: https://trustedcomputinggroup.org/resource/tpm-library-specification/
- **TSS 2.0 Overview**: https://trustedcomputinggroup.org/resource/tss-overview-common-structures-specification/

### API Specifications
- **ESAPI Specification**: https://trustedcomputinggroup.org/resource/tss-2-0-enhanced-system-api-esapi-specification/
- **SAPI Specification**: https://trustedcomputinggroup.org/resource/tss-2-0-system-level-api-sapi-specification/
- **FAPI Specification**: https://trustedcomputinggroup.org/resource/tss-feature-api-fapi-specification/

## Community Resources

### Mailing Lists
- **TPM2 Mailing List**: https://lore.kernel.org/tpm2/
- **Subscribe**: Send email to tpm2+subscribe@lists.linux.dev

### IRC Channel
- **#tpm2.0-tss** on FreeNode

### Weekly Calls
- **TPM.dev**: https://tpm.dev/ (weekly online discussions)

## Learning Path

### Beginner Level
1. Start with TPM2-Tools ReadTheDocs
2. Read the Quick Start guide
3. Practice with the commands you used (createprimary, create, load, evictcontrol)

### Intermediate Level
1. Understand TCTI configuration
2. Learn about TPM2-TSS APIs
3. Study the TPM2 concepts (hierarchies, PCRs, keys)

### Advanced Level
1. Read TCG specifications
2. Understand the TSS architecture
3. Contribute to the projects

## Commands You Used - Documentation

### `tpm2_createprimary`
- **Man Page**: https://tpm2-tools.readthedocs.io/en/latest/man/tpm2_createprimary.1.html
- **Purpose**: Create primary keys in TPM hierarchies

### `tpm2_create`
- **Man Page**: https://tpm2-tools.readthedocs.io/en/latest/man/tpm2_create.1.html
- **Purpose**: Create keys under parent keys

### `tpm2_load`
- **Man Page**: https://tpm2-tools.readthedocs.io/en/latest/man/tpm2_load.1.html
- **Purpose**: Load keys into TPM for use

### `tpm2_evictcontrol`
- **Man Page**: https://tpm2-tools.readthedocs.io/en/latest/man/tpm2_evictcontrol.1.html
- **Purpose**: Make keys persistent in TPM

### `tpm2_flushcontext`
- **Man Page**: https://tpm2-tools.readthedocs.io/en/latest/man/tpm2_flushcontext.1.html
- **Purpose**: Clear TPM contexts and free memory

## Environment Variables

### TSS2_TCTI
- **Purpose**: Controls TSS2 library TCTI
- **Format**: `<tcti-name>:<options>`
- **Examples**: `tabrmd:`, `swtpm:host=127.0.0.1,port=2321`

### TPM2TOOLS_TCTI
- **Purpose**: Controls tpm2-tools TCTI
- **Format**: `<tcti-name>:<options>`
- **Examples**: `tabrmd:`, `swtpm:host=127.0.0.1,port=2321`

## Next Steps

1. **Read the TPM2-Tools documentation** to understand all available commands
2. **Explore the TSS2 API documentation** if you want to program with TPM2
3. **Join the mailing list** for community support
4. **Practice with different TPM2 operations** like PCRs, attestation, etc.

## Troubleshooting

- **Memory Issues**: Use `tpm2_flushcontext -t` to clear contexts
- **TCTI Issues**: Check environment variables and TCTI configuration
- **Permission Issues**: Ensure proper TPM access permissions
- **Emulator Issues**: Check swtpm logs and configuration 
- **DA Lockout Mode**:  
  If you encounter DA (Dictionary Attack) lockout mode (often indicated by errors related to TPM authorization or failed attempts), you will need to reset the lockout state. To do this, open a shell in the running container (e.g., using `docker exec -it <container_name> /bin/bash`) and run the following command to clear lockout and set a high maximum tries value:

  ```
  tpm2_dictionarylockout --setup-parameters --max-tries=4294967295 --clear-lockout
  ```

  This command clears any lockout and increases the allowed number of failed authorization attempts, greatly reducing the chance of future lockout events. Make sure you have the necessary TPM permissions inside the container to execute this command.



