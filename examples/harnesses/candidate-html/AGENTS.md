# AGENTS.md

General engineering guidance for work in this project.

## Code quality

- Follow DRY principles. Do not duplicate structure that can exist once.
- Keep the implementation simple, readable and maintainable. Prefer the smallest thing
  that does the job over a larger thing that does more.
- Do not leave dead, placeholder or commented-out markup behind.

## HTML

- Use semantic HTML5 elements for what they mean, rather than generic containers with
  class names describing the same thing.
- Consider accessibility when creating forms. Think about how someone using a screen
  reader, or navigating by keyboard, will encounter each control you add.
- Produce a valid HTML5 document.

## Fitting in with what is already here

- Preserve existing project conventions. Before writing a new page, look at how the pages
  already in the project are put together and follow the same shape.
- Where the project has already made a choice, follow it rather than introducing a second
  way of doing the same thing.

## Before you finish

- Validate your implementation.
- If validation reports a problem, fix the cause and validate again.
