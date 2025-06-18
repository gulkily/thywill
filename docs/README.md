# ThyWill Documentation

This directory contains all documentation for the ThyWill prayer application.

## Documentation Structure

### 📁 **implementation/**
Active implementation plans and technical specifications
- `SCHEMA_ONLY_MIGRATIONS_PLAN.md` - Plan to fix logout/account issues during upgrades

### 📁 **operations/**
Deployment, hosting, and operational guides
- `DATABASE_PROTECTION.md` - Database backup and protection strategies
- `DEPLOYMENT_WORKFLOW.md` - Step-by-step deployment procedures
- `UBUNTU_HOSTING_GUIDE.md` - Ubuntu server setup and hosting guide

### 📁 **guides/**
User and developer guides
- `MULTI_DEVICE_AUTH_GUIDE.md` - Multi-device authentication setup
- `TEXT_ARCHIVE_DOCUMENTATION.md` - Text archive system documentation

### 📁 **plans/**
Feature specifications and development plans
- Active development plans for new features
- Technical specifications for enhancements
- Implementation roadmaps

### 📁 **testing/**
Testing documentation and procedures
- Test plans and coverage analysis
- Manual testing guides
- Unit test documentation

### 📁 **archived/**
Historical plans and completed implementations
- Completed development plans
- Legacy documentation
- Reference materials

## Quick Links

### 🚨 **Current Issues**
- [Schema-Only Migrations Plan](implementation/SCHEMA_ONLY_MIGRATIONS_PLAN.md) - **PRIORITY**: Fix user logout during upgrades

### 🛠 **Operations**
- [Deployment Guide](../deployment/DEPLOYMENT_GUIDE.md) - How to deploy ThyWill
- [Database Protection](operations/DATABASE_PROTECTION.md) - Backup and recovery procedures

### 👥 **For Developers**
- [AI Project Guide](../AI_PROJECT_GUIDE.md) - Development workflow and standards
- [Testing Plan](testing/TESTING_PLAN.md) - Testing procedures and coverage

### 📖 **For Users**
- [Installation Guide](../INSTALL.md) - How to install and set up ThyWill
- [Multi-Device Auth](guides/MULTI_DEVICE_AUTH_GUIDE.md) - Using ThyWill on multiple devices

## Document Status

### 🔥 **Active/Current**
- Schema-Only Migrations Plan
- Deployment Guide
- Multi-Device Auth Guide

### 📋 **Needs Review**
- Testing documentation
- Feature plans in `/plans/`

### 📚 **Reference**
- Database protection docs
- Text archive documentation
- Ubuntu hosting guide

## Contributing to Documentation

When adding new documentation:

1. **Choose the right location**:
   - `/implementation/` for active development plans
   - `/operations/` for deployment/hosting procedures
   - `/guides/` for user/developer guides
   - `/plans/` for future feature specifications

2. **Use clear filenames**:
   - ALL_CAPS_WITH_UNDERSCORES for major documents
   - descriptive-lowercase-names for specific guides

3. **Update this README** when adding significant new documents

4. **Archive completed plans** by moving them to `/archived/`

---

*Last updated: December 2024*