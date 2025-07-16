# PGP Migration Plan for ThyWill Authentication

## Current State Analysis

### Current System Issues
- **Homegrown Ed25519**: Custom implementation with timestamp conversion bugs
- **Key Management**: No standard key distribution/trust model
- **Verification Complexity**: Custom canonical content reconstruction
- **Limited Tooling**: Custom verification scripts with edge cases
- **No Prayer Marks Verification**: Missing signature verification for prayer marks

### Git vs File-Based Archives Consideration
**Git-based archives would provide:**
- Built-in cryptographic integrity (SHA-256 commit hashes)
- Automatic tamper detection via commit history
- Standard tooling for verification (`git log --show-signature`)
- Distributed backup through remote repositories
- Native support for PGP signing (`git commit -S`)

**Recommendation**: Migrate to Git-based archives with PGP signing for ultimate integrity and industry-standard verification.

## Proposed PGP Migration

### Phase 1: PGP Infrastructure Setup

#### 1.1 Key Management
- **User Key Generation**: Each user generates GPG keypair on registration
- **Key Storage**: 
  - Private keys remain on user devices (never server-side)
  - Public keys stored in database and exported to Git repo keyring
- **Key Distribution**: Public keyring file in Git repository
- **Trust Model**: Web of trust starting from admin keys

#### 1.2 Archive Structure Migration
```
text_archives/
├── .git/                    # Git repository
├── keyring/                 # Public keys
│   ├── users.gpg           # All user public keys
│   └── admins.gpg          # Admin public keys
├── prayers/                 # Signed prayer files
│   └── 2025/
│       └── 07/
│           └── prayer_20250711_0118.txt.asc  # PGP signed
└── verification/
    └── verify_pgp.py       # PGP verification tools
```

### Phase 2: Prayer Submission with PGP

#### 2.1 Prayer Signing Process
1. **Client-side**: User submits prayer text
2. **Server generates**: Canonical prayer content
3. **Client signs**: PGP signature of canonical content
4. **Server stores**: Prayer + detached signature
5. **Archive creation**: PGP-signed text file committed to Git

#### 2.2 Canonical Content Format
```
PRAYER_SUBMISSION
Prayer ID: {prayer_id}
Submitted: {iso_timestamp}
Author: {user_id}
Request: {original_request}
Generated: {generated_prayer}
```

### Phase 3: Prayer Marks with PGP

#### 3.1 Prayer Mark Signing
- **Action**: User marks prayer (prayed/answered/etc.)
- **Canonical Format**:
  ```
  PRAYER_MARK
  Prayer ID: {prayer_id}
  Action: {mark_type}
  Timestamp: {iso_timestamp}
  Marker: {user_id}
  ```
- **Signature**: Attached PGP signature in the same file
- **Storage**: Signature stored in database and archive

#### 3.2 Multi-User Prayer Marks
- **Individual Signatures**: Each user signs their own mark
- **Aggregate Verification**: Verify all marks against respective public keys
- **Archive Format**:
  ```
  Activity:
  2025-07-11T01:18:00Z - alice prayed this prayer
  -----BEGIN PGP SIGNATURE-----
  [Alice's signature]
  -----END PGP SIGNATURE-----
  
  2025-07-11T02:30:00Z - bob marked this answered
  -----BEGIN PGP SIGNATURE-----
  [Bob's signature]
  -----END PGP SIGNATURE-----
  ```

### Phase 4: Git-Based Archive Integrity

#### 4.1 Commit Signing
- **Every archive commit**: Signed by server admin key
- **Verification**: `git log --show-signature` shows all signatures
- **Tamper Detection**: Any modification breaks commit chain

#### 4.2 Archive Structure
```
commit a1b2c3d4 (HEAD -> main)
Author: ThyWill Server <admin@thywill.org>
Date:   Fri Jul 11 01:18:00 2025 +0000
GPG:    using RSA key 1234567890ABCDEF
GPG:    Good signature from "ThyWill Server <admin@thywill.org>"

    Add prayer b94f7b7be56b46928973eaafa2c6ed6a
    
    - Original request: "please help me tet cryptoo system"
    - Author: ilyag
    - Timestamp: 2025-07-11T01:18:00Z
    - Signatures: 1 prayer, 1 mark
```

### Phase 5: Verification Tools

#### 5.1 PGP Verification Script
```python
# verify_pgp_archives.py
def verify_prayer_file(filepath):
    """Verify PGP signatures in prayer archive file"""
    # Parse prayer content and embedded signatures
    # Verify each signature against keyring
    # Return verification results

def verify_git_commits():
    """Verify all Git commit signatures"""
    # Use git log --show-signature
    # Verify admin signatures on all commits
    # Detect any unsigned or invalid commits
```

#### 5.2 Integration with Existing Tools
- **CLI Command**: `./thywill crypto verify-pgp`
- **Git Integration**: `git log --show-signature`
- **Automated Checks**: Pre-commit hooks for signature verification

## Migration Strategy

### Phase A: Dual System (2-3 months)
1. Keep existing Ed25519 system running
2. Implement PGP signing alongside
3. All new prayers signed with both systems
4. Verify both signature types during transition

### Phase B: PGP Primary (1 month)
1. Switch to PGP-only for new prayers
2. Migrate archives to Git repository
3. Implement PGP verification tools
4. Update all client code to use PGP

### Phase C: Legacy Cleanup (1 month)
1. Remove Ed25519 code paths
2. Migrate historical archives (best effort)
3. Update documentation
4. Final verification of all archives

## Benefits of PGP + Git Approach

### Security
- **Industry Standard**: Battle-tested cryptographic protocols
- **Key Management**: Established GPG key distribution
- **Verification**: Standard tools (`gpg --verify`, `git log --show-signature`)
- **Tamper Detection**: Git commit hashes prevent silent modification

### Operational
- **Tooling**: Rich ecosystem of PGP tools
- **Backup**: Git remotes provide automatic distributed backup
- **Auditability**: Complete history with cryptographic proof
- **Debugging**: Standard tools for signature troubleshooting

### Scalability
- **Multi-User**: Each user manages their own keys
- **Trust Networks**: Web of trust for key validation
- **Archive Size**: Git compression reduces storage needs
- **Performance**: Efficient verification with established libraries

## Implementation Timeline

- **Month 1**: PGP infrastructure setup, key generation
- **Month 2**: Dual signing implementation, testing
- **Month 3**: Git archive migration, verification tools
- **Month 4**: PGP-only mode, legacy cleanup
- **Month 5**: Documentation, final verification

## Risks and Mitigations

### Key Management Complexity
- **Risk**: Users lose private keys
- **Mitigation**: Key backup procedures, recovery workflows

### Migration Data Loss
- **Risk**: Historical archive corruption during migration
- **Mitigation**: Complete backup before migration, parallel verification

### Performance Impact
- **Risk**: PGP signing slower than Ed25519
- **Mitigation**: Benchmark and optimize, async signing

## Conclusion

**Recommendation**: Migrate to PGP + Git-based archives for industry-standard cryptographic integrity, better tooling, and automatic tamper detection. The combination provides both content authenticity (PGP) and structural integrity (Git) with standard verification tools.