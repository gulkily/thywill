# Persistent Changelog Entries - Feature Description

## Problem Statement
The current changelog system generates AI descriptions dynamically per server, creating inconsistency across environments and losing production-curated entries during server rebuilds.

## User Stories
- As a **user**, I want to see consistent changelog descriptions across all servers so that I get the same information regardless of environment
- As an **administrator**, I want to preserve manually curated changelog entries so that production improvements aren't lost during deployments
- As a **developer**, I want changelog entries stored as human-readable text files so that I can easily review and edit them in any text editor
- As a **site operator**, I want to migrate existing production changelog entries so that historical context is preserved
- As a **content manager**, I want to manually edit changelog descriptions through simple text files so that I can improve clarity without technical barriers

## Core Requirements
- Store changelog entry descriptions as individual .txt files in `changelog/entries/` directory, named by commit hash
- Each text file contains structured but human-readable content (description, type, date)
- Maintain backward compatibility with existing database entries during transition
- Provide migration tool to export existing production changelog entries to text files
- Enable manual editing of changelog descriptions through standard text editor workflow

## User Flow
1. Developer commits code changes to repository
2. Changelog text file is created (manually or through tooling) in `changelog/entries/{commit_hash}.txt`
3. Text file contains user-friendly description and metadata in readable format
4. Deployment process includes changelog files, ensuring consistent descriptions across servers
5. Users see identical changelog descriptions regardless of server environment
6. Administrators edit changelog text files directly in repository to improve descriptions

## Success Criteria
- Changelog descriptions are identical across development, staging, and production environments
- Existing production changelog entries are successfully exported to text files and preserved
- Manual editing of changelog descriptions requires only a text editor and basic git knowledge
- Zero data loss during migration from dynamic AI generation to static text file storage
- System falls back gracefully to database entries when text files don't exist (backward compatibility)