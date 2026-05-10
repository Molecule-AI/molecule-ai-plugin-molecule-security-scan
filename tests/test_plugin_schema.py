#!/usr/bin/env python3
"""
Schema validation tests for molecule-security-scan.

Tests plugin.yaml structure, SKILL.md frontmatter, file existence,
and known-issues.md format. No external dependencies or network needed.

Run: python tests/test_plugin_schema.py
Or:  python -m pytest tests/test_plugin_schema.py -v
"""
import os
import re
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, '.molecule-ci', 'scripts'))


class TestPluginYamlSchema(unittest.TestCase):
    """Validate plugin.yaml structure and required fields."""

    @classmethod
    def setUpClass(cls):
        import yaml
        plugin_yaml_path = os.path.join(REPO_ROOT, 'plugin.yaml')
        with open(plugin_yaml_path) as f:
            cls.plugin = yaml.safe_load(f)

    def test_plugin_yaml_loads(self):
        """plugin.yaml is valid YAML."""
        self.assertIsInstance(self.plugin, dict)

    def test_name_field_present(self):
        self.assertIn('name', self.plugin)
        self.assertEqual(self.plugin['name'], 'molecule-security-scan')

    def test_version_field_present(self):
        self.assertIn('version', self.plugin)
        self.assertIsInstance(self.plugin['version'], str)

    def test_version_format(self):
        import re
        v = self.plugin['version']
        self.assertRegex(v, r'^\d+\.\d+\.\d+$', f"Version {v!r} not semver")

    def test_description_present(self):
        self.assertIn('description', self.plugin)
        self.assertGreater(len(self.plugin['description']), 20)

    def test_runtimes_is_list(self):
        runtimes = self.plugin.get('runtimes')
        self.assertIsInstance(runtimes, list)
        self.assertIn('claude_code', runtimes)

    def test_skills_is_list(self):
        skills = self.plugin.get('skills', [])
        self.assertIsInstance(skills, list)
        self.assertIn('skill-cve-gate', skills)

    def test_tags_security_present(self):
        tags = self.plugin.get('tags', [])
        self.assertIsInstance(tags, list)
        security_tags = {'security', 'cve', 'supply-chain'}
        self.assertTrue(
            security_tags.intersection(tags),
            f"Expected security tags {security_tags} in {tags}"
        )


class TestSkillCveGate(unittest.TestCase):
    """Validate the skill-cve-gate SKILL.md."""

    SKILL_PATH = os.path.join(REPO_ROOT, 'skills', 'skill-cve-gate', 'SKILL.md')

    def test_skill_file_exists(self):
        self.assertTrue(os.path.isfile(self.SKILL_PATH), f"{self.SKILL_PATH} not found")

    def test_skill_has_frontmatter(self):
        import yaml
        with open(self.SKILL_PATH) as f:
            content = f.read()
        self.assertTrue(content.startswith('---'), "SKILL.md must have YAML frontmatter")
        parts = content.split('---', 2)
        self.assertEqual(len(parts), 3, "SKILL.md must have opening and closing ---")
        _, frontmatter, _ = parts
        data = yaml.safe_load(frontmatter)
        self.assertIsInstance(data, dict)

    def test_skill_frontmatter_name(self):
        import yaml
        with open(self.SKILL_PATH) as f:
            content = f.read()
        parts = content.split('---', 2)
        _, frontmatter, body = parts
        data = yaml.safe_load(frontmatter)
        self.assertEqual(data['name'], 'skill-cve-gate')

    def test_skill_frontmatter_description(self):
        import yaml
        with open(self.SKILL_PATH) as f:
            content = f.read()
        parts = content.split('---', 2)
        _, frontmatter, body = parts
        data = yaml.safe_load(frontmatter)
        self.assertIsInstance(data.get('description'), str)
        self.assertGreater(len(data['description']), 20)

    def test_skill_body_has_heading(self):
        with open(self.SKILL_PATH) as f:
            content = f.read()
        parts = content.split('---', 2)
        _, _, body = parts
        # Body may have leading whitespace/newlines before the first heading
        self.assertRegex(body.lstrip(), r'^# ', "SKILL.md body must have a # heading")

    def test_skill_body_has_modes_section(self):
        with open(self.SKILL_PATH) as f:
            content = f.read()
        # Should document the off/warn/block modes
        self.assertIn('mode:', content)
        self.assertIn('off', content)
        self.assertIn('warn', content)
        self.assertIn('block', content)


class TestKnownIssues(unittest.TestCase):
    """Validate known-issues.md structure."""

    KI_PATH = os.path.join(REPO_ROOT, 'known-issues.md')

    def test_file_exists(self):
        self.assertTrue(os.path.isfile(self.KI_PATH))

    def test_has_active_issues_section(self):
        with open(self.KI_PATH) as f:
            content = f.read()
        self.assertIn('Active Issues', content)

    def test_has_recently_resolved_section(self):
        with open(self.KI_PATH) as f:
            content = f.read()
        self.assertIn('Recently Resolved', content)

    def test_has_severity_definitions(self):
        with open(self.KI_PATH) as f:
            content = f.read()
        self.assertIn('Severity Definitions', content)
        # P0-P3 defined
        self.assertIn('P0', content)
        self.assertIn('P1', content)
        self.assertIn('P2', content)
        self.assertIn('P3', content)


class TestReadme(unittest.TestCase):
    """Validate README.md has required sections."""

    README_PATH = os.path.join(REPO_ROOT, 'README.md')

    def test_readme_exists(self):
        self.assertTrue(os.path.isfile(self.README_PATH))

    def test_readme_has_h1(self):
        with open(self.README_PATH) as f:
            first_line = f.readline().strip()
        self.assertTrue(first_line.startswith('# '), f"README must start with # heading, got: {first_line!r}")

    def test_readme_has_install_section(self):
        with open(self.README_PATH) as f:
            content = f.read()
        self.assertIn('Install', content)
        self.assertIn('plugins', content)

    def test_readme_has_configuration_section(self):
        with open(self.README_PATH) as f:
            content = f.read()
        self.assertIn('config', content.lower())

    def test_readme_has_runtime_section(self):
        with open(self.README_PATH) as f:
            content = f.read()
        self.assertIn('claude_code', content)


class TestValidatePluginScript(unittest.TestCase):
    """Smoke-test the validate-plugin.py script."""

    def test_validate_plugin_exits_zero(self):
        import subprocess
        result = subprocess.run(
            [sys.executable, os.path.join(REPO_ROOT, '.molecule-ci', 'scripts', 'validate-plugin.py')],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        self.assertEqual(result.returncode, 0, f"validate-plugin.py failed:\nstdout: {result.stdout}\nstderr: {result.stderr}")
        self.assertIn('molecule-security-scan', result.stdout)


if __name__ == '__main__':
    unittest.main(verbosity=2)
