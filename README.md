# Gujju-Gang-CP1

Hello everyone, this is the private repository for our project.
As suggest we have to collabratively complete this project. I have made repo for collabrative and convenient work. Mind that this will be useful at placements.

## Directory Structure

```
Team_num18
    ├── 📁 Charlib
    ├── 📁 Layout
    ├── 📁 LEF
    ├── 📁 LIB
    ├── 📁 Verilog
    ├── 📁 Spice_Netlist
    ├── 📁 Reports
    ├── Combinational_Lib.docx
    ├── Sequential_Lib.docx
    ├── Course_Project_1.pdf
    └── README.md
```
## Guidelines
- You can commit at you choice. Please atleast commit after complete the file or at the end of the day.
- The directory structure is standard, which is given in the pdf. Add your personal files and build files in gitignore.
- I will use Markdown for the reporting, then later we convert it into latex using pandoc software.
- You can change other's file because it's git :) Or you can create issues and assign a task to others.

## Project

- [ ] inv: Inverter
- [ ] dfxtn:	Delay flop, single output Q, negedge clk
- [ ] nand3b:	3-input NAND, first input inverted

## Flow of working

### 1. Create issue
- Create new issue which is not present the repository. 
- Add lables, Milestones, Relations, etc.
- Assign this to yourself or any teammate.

### 2. Create branch
- Create banch in the devlopment section and pull it in local repo.
- Switch to that branch and start working on it.

### 3. Merge
- Use `git push` on that banch.
- After completing the isssue, goto pull request and create one.
- You can delete parent branch or stay as it is.
- Start working on next issue.

## Deliverables

- [x] Project Plan and assignment
- [x] Report Skeleton
- [ ] Spice Netlist
  - [x] inv
  - [x] dfxtn
  - [ ] nand3b
- [ ] Verilog code
  - [ ] inv
  - [ ] dfxtn
  - [ ] nand3b
- [ ] Draw the layout
  - [x] inv
  - [x] dfxtn
  - [ ] nand3b
- [ ] Export the LEF
  - [ ] inv
  - [ ] dfxtn
  - [ ] nand3b
- [ ] Export the LIB
  - [ ] inv
  - [ ] dfxtn
  - [ ] nand3b
- [ ] Report Writing

## FAQs

1. I can't access
  - Port 22 is blocked by IIT Bombay. So update the port in ssh using AI, or use personal hospot or you can use https.
  - If still problem. Request project owner.

2. Command for md to pdf
```bash 
pandoc temp.md --template=template.tex -o output.pdf --pdf-engine=lualatex --filter pandoc-crossref --lua-filter=inline.lua 
```
