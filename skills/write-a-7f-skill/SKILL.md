---
name: write-a-7f-skill
description: Write or revise a 7Factor Software agent skill using Matt Pocock's skill-writing discipline and 7Factor's immutable-host script standard.
compatibility: Requires filesystem access and a client supporting Claude-compatible manual skill invocation; best with /writing-great-skills installed.
argument-hint: "[skill request]"
disable-model-invocation: true
---

# Write a 7Factor Skill

## Load the craft discipline

Use Matt Pocock's `/writing-great-skills` as the primary authoring discipline. Fall back to the legacy `/write-a-skill`
when that is the installed option. Treat that companion skill as the single source of truth for invocation, information
hierarchy, completion criteria, progressive disclosure, leading words, and pruning; this skill supplies only the
7Factor overlay.

1. Prefer guidance already active in the current turn.
2. Invoke an available model-invoked companion skill. A user-invoked companion can only be activated by the user; if it
   is installed but inactive, pause and ask the user to invoke it alongside this skill.
3. If neither companion is installed, pause before authoring and strongly recommend installing
   [`mattpocock/skills`](https://github.com/mattpocock/skills):

   ```sh
   npx skills@latest add mattpocock/skills
   ```

   Ask the user to select `/writing-great-skills`, then rerun the request with both skills. Continue without Matt's
   discipline only after the user explicitly declines.

This gate is complete when Matt's current or legacy guidance is active, or the user has explicitly declined it.

## Author the skill

1. Read the request, repository instructions, neighboring skills, and the existing target before asking questions.
   Establish concrete uses, destination, public or private status, invocation choice, and required resources. For a
   public skill in this repository, use `skills/<skill-name>/`. This step is complete when every choice that would
   materially change the skill is resolved.
2. Design the skill with the active Matt guidance. Keep steps and their checkable completion criteria in `SKILL.md`;
   disclose branch-specific reference behind explicit context pointers; remove duplication, sediment, and no-ops. This
   step is complete when every instruction has one authoritative home and every branch is reachable.
3. Select frontmatter from the target agent's current schema using the standard below. This step is complete when every
   included field changes discovery, execution, compatibility, permissions, or presentation for a known consumer, and
   the target validator accepts it.
4. Decide whether deterministic or repeated operations justify bundled scripts. When they do, apply the entire
   immutable-host standard below before writing them. This step is complete when each script has one documented
   dispatch flow with a verified local probe and Docker fallback, callable from POSIX and native Windows command
   environments without depending on the runtime being probed.
5. Create or edit only the files the skill needs. Test bundled scripts through their documented dispatch flow, and
   update any generated agent metadata only when the skill owns it. This step is complete when no placeholders or
   unused resources remain and every changed file contributes to the skill.
6. Validate the skill with the repository's validator when available, inspect the final diff, and test every execution
   branch in POSIX and native Windows command environments locally or in CI. This step is complete when validation
   passes, every rule in this skill has been applied, and any portable execution path that could not be tested is
   reported as a blocker rather than assumed to work.

## Frontmatter standard

Identify every intended agent before selecting fields. Check the current
[Agent Skills specification](https://agentskills.io/specification) for portable fields and each target agent's official
documentation for extensions; never infer support from another agent's parser.

- Start with portable `name` and `description`. Add `license`, `compatibility`, `metadata`, or the experimental
  `allowed-tools` only when the field has a concrete consumer. Use `compatibility` for intended products, required
  local runtimes, Docker alternatives, system packages, architecture, and network access. Most skills need no
  compatibility declaration.
- For a cross-agent skill, keep required behavior in the portable body. Treat implementation-specific fields as
  optional enhancements, and verify strict target validators accept them.
- For a Claude-targeted skill, consult the current
  [Claude Code skill frontmatter reference](https://code.claude.com/docs/en/slash-commands). Consider invocation fields
  (`disable-model-invocation`, `user-invocable`), arguments (`argument-hint`, `arguments`), permissions
  (`allowed-tools`, `disallowed-tools`), execution (`model`, `effort`, `context`, `agent`), and scoping (`hooks`,
  `paths`, `shell`) only when the corresponding behavior is intentional. Remember that Claude's `allowed-tools`
  pre-approves tools; it does not restrict the remaining tool set.
- Omit defaults, decorative metadata, guessed fields, and permissions broader than the skill requires. Validate against
  every declared target, not merely the authoring agent.

## Immutable-host script standard

Treat the user's host as immutable. Execute with dependencies that are already available, or execute inside Docker.
Package managers, runtime managers, virtual environments, shell profiles, `PATH`, and system configuration on the host
remain untouched. The sole exception is a skill whose declared purpose is to install or configure the host environment.

### Portable dispatch

Issue runtime probes and Docker commands through the command environment already available to the agent. The dispatcher
must not depend on the runtime it probes and must be callable from both a POSIX shell and a native Windows command
environment.

For agent-invoked scripts, put the dispatch flow in the skill body so the agent can adapt its syntax to the current
command environment. Hooks and other automatic entry points need launchers callable from both environments.

### Classify the runtime

- **Simple**: a runtime plus its standard library, or another small dependency set already supplied by one trusted base
  image.
- **Complex**: language packages, native libraries, external executables such as Graphviz or FFmpeg, services, compiled
  extensions, or a dependency set whose installation varies by platform.

### Simple runtime

1. From the portable dispatcher, directly execute a non-mutating probe for the exact runtime, supported version,
   required capabilities, and intended script invocation. For Bash, launch `bash -c "exit 0"` and syntax-check the
   script with `bash -n path/to/script.sh`; executable discovery alone is not a complete probe.
2. Use the local runtime only when the complete probe passes.
3. Otherwise, verify both the Docker client and daemon, then run the script in a named official or otherwise trusted
   image pinned to a version and preferably an immutable digest.
4. If Docker is unavailable or unusable, stop and tell the user to configure the required local runtime or install and
   start Docker. Do not attempt either change.

### Complex runtime

1. Probe every runtime, executable, library, and material capability without changing the host. A small import or
   execution smoke test is stronger than version checks alone.
2. Use the local path only when the whole probe passes; otherwise use Docker.
3. For a private or unpublished image, include a Dockerfile, locked dependency inputs, and one dispatcher, expressed
   through portable launchers where necessary, that performs the probe and fallback. Pin the base image by digest
   and dependencies as tightly as the ecosystem permits.
4. Build the fallback image through that dispatcher on every Docker execution. Let Docker's content cache make
   unchanged builds cheap and invalidate layers when the Dockerfile or locked inputs change. Prefer mounting the
   current scripts into an environment-only image; then script changes take effect immediately without rebuilding the
   environment. If scripts are copied into the image, the always-build dispatcher must include them in the build
   context.
5. For a public skill, prefer a published multi-architecture environment image from a trusted registry, referenced by
   immutable digest. Publish a new image when the Dockerfile or locked environment inputs change, then update the
   digest in the dispatcher. Mount the skill's current scripts rather than baking them into the image when practical.
6. Use Docker Compose only when the runtime genuinely needs multiple containers, networks, or persistent services. For
   a single script environment, a dispatcher around `docker build` and `docker run` is the smaller contract. When
   Compose is justified, have the dispatcher build before `run` or `up`, or reference published images by immutable
   digest.

### Container contract

- Route every script invocation through the same documented dispatch flow so the local probe and fallback cannot drift.
  Launcher syntax may differ between command environments, but each entry point must implement that same flow.
- Use `--rm`, least-privilege settings, a non-root user when practical, and only the exact mounts required for inputs
  and outputs. Avoid privileged mode, the host Docker socket, and broad home-directory mounts.
- State the image reference, required mounts, inputs, outputs, supported architectures, and failure message in the
  skill. A failed pull or build is a blocker to report, not permission to install host dependencies.
- Test the local path when its probe passes and the Docker path whenever Docker is available. When Docker is absent and
  the fallback is required, stop with the environment-or-Docker choice instead of declaring the skill complete.
