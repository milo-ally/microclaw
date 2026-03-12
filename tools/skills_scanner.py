from pathlib import Path

import yaml

from microclaw.config import get_base_dir


def scan_skills(base_dir: Path | str | None = None) -> str: 
    """Scan all SKILL.md files and generate SKILL_SNAPSHOT.md"""
    base_dir = Path(base_dir or get_base_dir())
    skills_dir = base_dir / "skills" 
    snapshot_path = skills_dir / "SKILL_SNAPSHOT.md" 

    if not skills_dir.exists():
        skills_dir.mkdir(parents=True)

    skills = [] 
    for skill_md in sorted(skills_dir.rglob("SKILL.md")):
        try: 
            content = skill_md.read_text(encoding="utf-8")
             # Parse YAML frontmatter 
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    meta = yaml.safe_load(parts[1])
                    if meta: 
                        rel_path = f"./skills/{skill_md.parent.name}/SKILL.md"
                        skills.append({
                            "name": meta.get("name", skill_md.stem), 
                            "description": meta.get("description", ""),
                            "location": rel_path
                        })
        except Exception as e:
            print(f"Error parsing {skill_md}: {str(e)}")

    # Build XML-style snapshot 
    lines = ["<available_skills>"] 
    for skill in skills: 
        lines.append(f"  <skill>")
        lines.append(f"    <name>{skill['name']}</name>")
        lines.append(f"    <description>{skill['description']}</description>")
        lines.append(f"    <location>{skill['location']}</location>")
        lines.append(f"  </skill>")
    lines.append("</available_skills>")

    snapshot = "\n".join(lines)
    snapshot_path.write_text(snapshot, encoding="utf-8")
    # print(f"Generated SKILL_SNAPSHOT.md with {len(skills)} skills")
    return snapshot 

# test
if __name__ == "__main__":
    snapshot = scan_skills()
    print(snapshot)
    print("skills_scanner ok")

    
