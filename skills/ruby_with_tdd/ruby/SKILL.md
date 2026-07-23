---
description: Drive Ruby work using TDD, Clean Code, and expressive naming. Run RuboCop on every change. Use when the user wants to write clean, well-tested Ruby with red-green-refactor and linting discipline.
allowed-tools: Bash Read Edit Write
---

## How to use these skills

TDD happens in three separate commands. Each one does exactly one thing:

- `/red` — write one failing test, run it, stop
- `/green` — write the minimum code to pass it, run the suite, stop
- `/refactor` — clean up and lint, stop

Start a cycle with `/red`. Do not proceed to the next command until you have the output from the previous one.

---

## The Standard

Every change must satisfy three things before it is done:
1. Tests are green.
2. RuboCop reports no offenses on changed files.
3. The code reads like well-written prose — names explain intent, methods do one thing, nothing is surprising.

---

## Object-Oriented Programming

- **Encapsulation** — hide internal state. Expose only what callers need. Prefer private methods and instance variables over public accessors.
- **Abstraction** — expose what a thing does, not how it does it. Names and interfaces should describe intent; implementation details stay hidden.
- **Inheritance** — use for genuine is-a relationships only. Prefer composition when the goal is code reuse rather than a true type hierarchy.
- **Polymorphism** — design so callers don't need to know which concrete class they're working with. Use duck typing in Ruby — if it responds to the right methods, it works.
- **Tell, don't ask** — tell objects to do things rather than querying their state and deciding for them. Keep decision logic inside the object that owns the data.
- **Law of Demeter** — only talk to your immediate collaborators. A chain like `a.b.c.d` is a smell; the object in the middle should expose the behavior you need directly.

---

## SOLID Principles

- **Single Responsibility** — a class or module does one thing. If you need "and" to describe what it does, split it.
- **Open/Closed** — extend behavior by adding new classes, not by modifying existing ones. Prefer composition over conditionals inside a class.
- **Liskov Substitution** — subclasses must be substitutable for their parent without changing program correctness. Don't override methods in ways that violate the parent's contract.
- **Interface Segregation** — don't force callers to depend on methods they don't use. Small, focused interfaces beat large, general ones.
- **Dependency Inversion** — depend on abstractions, not concretions. Inject dependencies rather than instantiating them inside a class.

---

## Clean Code Rules

**Names**
- Names must explain intent. If a name needs a comment to clarify it, the name is wrong.
- Methods: verb phrases (`decrypt_cookie`, `user_id_from_header`). Booleans: predicate form (`ignored?`, `valid?`). Classes: nouns.
- No abbreviations unless the abbreviation is more familiar than the full word (e.g. `url`, `id`).

**Methods**
- One method, one responsibility. If you need "and" to describe what it does, split it.
- Short. If a method doesn't fit comfortably in view, it is doing too much.
- No surprise side effects. A method named `get_x` must not mutate state or trigger I/O.

**Arguments**
- Fewer is better. More than three arguments is a design smell — consider a parameter object.
- No boolean flags as arguments. A flag argument means the method does two things.

**Comments**
- No comments that restate what the code already says.
- A comment is only justified when it explains WHY — a hidden constraint, a non-obvious invariant, a workaround for a specific external behavior.

**Structure**
- Delete dead code. Version control has it if you need it back.
- Duplication: two similar things may just be similar. Three identical things need abstraction.
- Don't abstract prematurely. Three similar lines is better than a wrong abstraction.

---

## RuboCop Rules

- Run RuboCop on every file you touch before declaring a cycle done.
- Fix all offenses — do not add `rubocop:disable` comments unless the offense is a confirmed false positive, and explain why inline.
- If RuboCop and Clean Code conflict, fix the code so both are satisfied rather than suppressing the cop.

---

## Collaboration

- Do not avoid conflict. If you disagree with the user's approach — on naming, design, test strategy, or anything else — say so directly and explain why. State your honest position once, clearly. If the user pushes back, engage with their reasoning rather than capitulating to avoid friction. Changing your position is fine; changing it just because the user pushed is not.

---

## Shared Rules (enforced across all three commands)

- Prefer RSpec unless the project already uses Minitest — follow what exists.
- One assertion per test where possible. Descriptive `it` names that read as sentences.
- Never define tests inside a loop. Use `shared_examples` with `include_examples` instead.
- Prefer real classes over test doubles. Doubles that mock an entire chain hide whether the real API is being used correctly.
- Never mock the class under test. If a method needs to be isolated, extract it into a collaborator and mock that instead.
- If the user asks to skip a step, decline and explain why the discipline matters.
