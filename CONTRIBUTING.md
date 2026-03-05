# Contributing to Agent Factory

Thank you for your interest in contributing! 🎉

## 🌍 Language

- **Code comments**: English preferred
- **Documentation**: Both English and Chinese are welcome
- **Commit messages**: English preferred
- **Issues/PRs**: Any language is fine

## 🚀 Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/meta-agent.git`
3. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
4. Create a feature branch: `git checkout -b feature/your-feature`

## 📝 Development Guidelines

### Directory Structure

- `source/meta-*/` - Core component Agents (public)
- `source/[other]/` - Business Agents (private, gitignored)
- `scripts/` - Shared utility scripts
- `.cursor/`, `.codebuddy/`, `.claude/` - IDE-specific configurations

### Code Style

- Python: Follow PEP 8
- Use type hints where possible
- Add docstrings for public functions

### Commit Messages

Use conventional commits format:
```
feat: add new feature
fix: fix a bug
docs: update documentation
refactor: code refactoring
test: add tests
```

## 🔄 Pull Request Process

1. Ensure your code follows the project's coding standards
2. Update documentation if needed
3. Add tests for new features
4. Make sure all tests pass
5. Submit a PR with a clear description

## 🐛 Reporting Issues

When reporting issues, please include:
- Operating system and version
- Python version
- IDE being used (Cursor/CodeBuddy/Claude Code)
- Steps to reproduce
- Expected vs actual behavior

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.
