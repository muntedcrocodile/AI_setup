---
llm:
  - minimax m2.5
harness:
  - opencode
language:
  - c
  - cpp
---

- For C and C++ projects, always use a Makefile for building. Always place intermediate build objects in the `./build` directory. The `./build` directory should be added to the `.gitignore` file. When writing cpp always use a `.hpp` filetype to help distinguish between plain `.h` fiels used for plain c.