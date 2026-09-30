"""Offline regression checks for a single, portable skill package."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SkillContract(unittest.TestCase):
    def test_single_root_skill(self):
        skills = sorted(p.relative_to(ROOT).as_posix() for p in ROOT.rglob('SKILL.md'))
        self.assertEqual(skills, ['SKILL.md'])

    def test_metadata_and_size(self):
        path = ROOT / 'SKILL.md'
        self.assertTrue(path.exists(), 'A focused root SKILL.md is required')
        text = path.read_text(encoding='utf-8')
        self.assertTrue(text.startswith('---\n'))
        header, body = text[4:].split('\n---\n', 1)
        self.assertRegex(header, r'(?m)^version: [\"\']0\.1[\"\']$')
        self.assertRegex(header, r'(?m)^name: [a-z0-9-]{1,64}$')
        description = re.search(r'(?m)^description: "([^"]+)"$', header)
        if description is None:
            self.fail('Missing quoted description')
        self.assertLessEqual(len(description[1]), 60)
        self.assertTrue(description[1].endswith('.'))
        for field in ('author:', 'license: MIT', 'platforms:', 'tags:'):
            self.assertIn(field, header)
        for heading in ('## When to Use', '## Procedure', '## Pitfalls', '## Verification'):
            self.assertIn(heading, body)
        self.assertLessEqual(len(text.encode('utf-8')), 5000)
        self.assertLessEqual(len(text.splitlines()), 100)

    def test_portable_secret_free_files(self):
        for path in ROOT.rglob('*'):
            if not path.is_file() or '.git' in path.parts or '__pycache__' in path.parts:
                continue
            relative = path.relative_to(ROOT).as_posix()
            self.assertNotEqual(path.name, '.env', relative)
            self.assertNotIn('cache/', relative)
            if path.suffix != '.md':
                continue
            text = path.read_text(encoding='utf-8')
            self.assertIsNone(re.search(r'(?:github_pat_|ghp_)[A-Za-z0-9_]{20,}', text), relative)
            self.assertNotIn('/opt/data/', text, relative)
            self.assertNotIn('/opt/hermes/', text, relative)


if __name__ == '__main__':
    unittest.main()
