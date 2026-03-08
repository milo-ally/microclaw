<available_skills>
  <skill>
    <name>algorithmic-art</name>
    <description>Creating algorithmic art using p5.js with seeded randomness and interactive parameter exploration. Use this when users request creating art using code, generative art, algorithmic art, flow fields, or particle systems. Create original algorithmic art rather than copying existing artists' work to avoid copyright violations.</description>
    <location>./skills/algorithmic-art/SKILL.md</location>
  </skill>
  <skill>
    <name>brand-guidelines</name>
    <description>Applies Anthropic's official brand colors and typography to any sort of artifact that may benefit from having Anthropic's look-and-feel. Use it when brand colors or style guidelines, visual formatting, or company design standards apply.</description>
    <location>./skills/brand-guidelines/SKILL.md</location>
  </skill>
  <skill>
    <name>canvas-design</name>
    <description>Create beautiful visual art in .png and .pdf documents using design philosophy. You should use this skill when the user asks to create a poster, piece of art, design, or other static piece. Create original visual designs, never copying existing artists' work to avoid copyright violations.</description>
    <location>./skills/canvas-design/SKILL.md</location>
  </skill>
  <skill>
    <name>doc-coauthoring</name>
    <description>Guide users through a structured workflow for co-authoring documentation. Use when user wants to write documentation, proposals, technical specs, decision docs, or similar structured content. This workflow helps users efficiently transfer context, refine content through iteration, and verify the doc works for readers. Trigger when user mentions writing docs, creating proposals, drafting specs, or similar documentation tasks.</description>
    <location>./skills/doc-coauthoring/SKILL.md</location>
  </skill>
  <skill>
    <name>docx</name>
    <description>Use this skill whenever the user wants to create, read, edit, or manipulate Word documents (.docx files). Triggers include: any mention of 'Word doc', 'word document', '.docx', or requests to produce professional documents with formatting like tables of contents, headings, page numbers, or letterheads. Also use when extracting or reorganizing content from .docx files, inserting or replacing images in documents, performing find-and-replace in Word files, working with tracked changes or comments, or converting content into a polished Word document. If the user asks for a 'report', 'memo', 'letter', 'template', or similar deliverable as a Word or .docx file, use this skill. Do NOT use for PDFs, spreadsheets, Google Docs, or general coding tasks unrelated to document generation.</description>
    <location>./skills/docx/SKILL.md</location>
  </skill>
  <skill>
    <name>frontend-design</name>
    <description>Create distinctive, production-grade frontend interfaces with high design quality. Use this skill when the user asks to build web components, pages, artifacts, posters, or applications (examples include websites, landing pages, dashboards, React components, HTML/CSS layouts, or when styling/beautifying any web UI). Generates creative, polished code and UI design that avoids generic AI aesthetics.</description>
    <location>./skills/frontend-design/SKILL.md</location>
  </skill>
  <skill>
    <name>internal-comms</name>
    <description>A set of resources to help me write all kinds of internal communications, using the formats that my company likes to use. Claude should use this skill whenever asked to write some sort of internal communications (status reports, leadership updates, 3P updates, company newsletters, FAQs, incident reports, project updates, etc.).</description>
    <location>./skills/internal-comms/SKILL.md</location>
  </skill>
  <skill>
    <name>mcp-builder</name>
    <description>Guide for creating high-quality MCP (Model Context Protocol) servers that enable LLMs to interact with external services through well-designed tools. Use when building MCP servers to integrate external APIs or services, whether in Python (FastMCP) or Node/TypeScript (MCP SDK).</description>
    <location>./skills/mcp-builder/SKILL.md</location>
  </skill>
  <skill>
    <name>pdf</name>
    <description>Use this skill whenever the user wants to do anything with PDF files. This includes reading or extracting text/tables from PDFs, combining or merging multiple PDFs into one, splitting PDFs apart, rotating pages, adding watermarks, creating new PDFs, filling PDF forms, encrypting/decrypting PDFs, extracting images, and OCR on scanned PDFs to make them searchable. If the user mentions a .pdf file or asks to produce one, use this skill.</description>
    <location>./skills/pdf/SKILL.md</location>
  </skill>
  <skill>
    <name>pptx</name>
    <description>Use this skill any time a .pptx file is involved in any way — as input, output, or both. This includes: creating slide decks, pitch decks, or presentations; reading, parsing, or extracting text from any .pptx file (even if the extracted content will be used elsewhere, like in an email or summary); editing, modifying, or updating existing presentations; combining or splitting slide files; working with templates, layouts, speaker notes, or comments. Trigger whenever the user mentions "deck," "slides," "presentation," or references a .pptx filename, regardless of what they plan to do with the content afterward. If a .pptx file needs to be opened, created, or touched, use this skill.</description>
    <location>./skills/pptx/SKILL.md</location>
  </skill>
  <skill>
    <name>skill-creator</name>
    <description>Create new skills, modify and improve existing skills, and measure skill performance. Use when users want to create a skill from scratch, update or optimize an existing skill, run evals to test a skill, benchmark skill performance with variance analysis, or optimize a skill's description for better triggering accuracy.</description>
    <location>./skills/skill-creator/SKILL.md</location>
  </skill>
  <skill>
    <name>slack-gif-creator</name>
    <description>Knowledge and utilities for creating animated GIFs optimized for Slack. Provides constraints, validation tools, and animation concepts. Use when users request animated GIFs for Slack like "make me a GIF of X doing Y for Slack."</description>
    <location>./skills/slack-gif-creator/SKILL.md</location>
  </skill>
  <skill>
    <name>task-planner</name>
    <description>帮助用户进行复杂任务规划、分解和跟踪的技能。当用户提出复杂需求、多步骤项目或需要系统化管理的任务时使用此技能。使用场景包括：项目规划、任务分解、进度跟踪、资源分配、时间估算等。当用户说"这个任务很复杂"、"需要规划一下"、"帮我分解任务"、"制定项目计划"、"项目管理"、"任务跟踪"、"进度管理"时，使用此技能。优先使用内置脚本工具来减少模型负担，提高执行效率。</description>
    <location>./skills/task-planner/SKILL.md</location>
  </skill>
  <skill>
    <name>theme-factory</name>
    <description>Toolkit for styling artifacts with a theme. These artifacts can be slides, docs, reportings, HTML landing pages, etc. There are 10 pre-set themes with colors/fonts that you can apply to any artifact that has been creating, or can generate a new theme on-the-fly.</description>
    <location>./skills/theme-factory/SKILL.md</location>
  </skill>
  <skill>
    <name>web-artifacts-builder</name>
    <description>Suite of tools for creating elaborate, multi-component claude.ai HTML artifacts using modern frontend web technologies (React, Tailwind CSS, shadcn/ui). Use for complex artifacts requiring state management, routing, or shadcn/ui components - not for simple single-file HTML/JSX artifacts.</description>
    <location>./skills/web-artifacts-builder/SKILL.md</location>
  </skill>
  <skill>
    <name>webapp-testing</name>
    <description>Toolkit for interacting with and testing local web applications using Playwright. Supports verifying frontend functionality, debugging UI behavior, capturing browser screenshots, and viewing browser logs.</description>
    <location>./skills/webapp-testing/SKILL.md</location>
  </skill>
  <skill>
    <name>xlsx</name>
    <description>Use this skill any time a spreadsheet file is the primary input or output. This means any task where the user wants to: open, read, edit, or fix an existing .xlsx, .xlsm, .csv, or .tsv file (e.g., adding columns, computing formulas, formatting, charting, cleaning messy data); create a new spreadsheet from scratch or from other data sources; or convert between tabular file formats. Trigger especially when the user references a spreadsheet file by name or path — even casually (like "the xlsx in my downloads") — and wants something done to it or produced from it. Also trigger for cleaning or restructuring messy tabular data files (malformed rows, misplaced headers, junk data) into proper spreadsheets. The deliverable must be a spreadsheet file. Do NOT trigger when the primary deliverable is a Word document, HTML report, standalone Python script, database pipeline, or Google Sheets API integration, even if tabular data is involved.</description>
    <location>./skills/xlsx/SKILL.md</location>
  </skill>
</available_skills>