# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development commands

```sh
# Run all tests (exit code 1 when a test fails or the run ends without a summary)
./run-tests

# Run a single test file (path relative to mygame/)
./run-tests tests/app/some_test.rb

# Lint (Ruby and gems come from mise.toml and the Gemfile)
bundle exec rubocop
```

The DragonRuby engine is not part of the repository: it gets copied into the repository root (see README.md), and `./dragonruby` must be there for tests and the game to run.

With `shaders=true` in `mygame/metadata/game_metadata.txt` the engine renders through SDL_GPU, which no headless SDL video driver provides (`dummy` and `offscreen` both fail with "Couldn't create render context"). `./run-tests` and `scripts/game start --headless` then cannot start the game; run the tests with a window instead, `SDL_AUDIODRIVER=dummy ./dragonruby mygame --test tests.rb`, and read the summary at the end of its output.

## Driving the running game

`scripts/game` starts its own instance of the game in the background and controls it through DragonRuby's development web server. Run it without arguments for all commands.

```sh
scripts/game start --headless   # without --headless the game gets a window; headless screenshots have no text labels
scripts/game press right a      # controller buttons through the engine's input path
scripts/game state              # tick plus whatever GameCli.state returns
scripts/game wait-until '<ruby expression>' [seconds]
scripts/game screenshot <name>  # saves mygame/tmp/game/screenshots/<name>.png
scripts/game reset [setup]      # restarts from tick 0, then runs GameCli.setup(:setup)
scripts/game stop
```

- It only touches the instance it started. `--attach` before a command uses whatever game listens on the port instead; that is usually the user's own session, so only use it when the user asks.
- Wait on game state with `wait-until`, never with `sleep`.
- A game can define a top-level `GameCli` module with `self.state` (a Hash added to `state`) and `self.setup(name)` (named starting points for `reset`). See README.md.

## Testing

`mygame/tests.rb` loads every file under `mygame/tests/` except `test_helper.rb`. Test files start with `require 'tests/test_helper'`.

`lib/spec_dsl.rb` is a small RSpec-like DSL on top of DragonRuby's test runner:

- `describe`/`context` group examples, `test`/`they` define them. `it 'name' do` is a syntax error in DragonRuby, which parses `it` as the implicit block parameter
- `before_each`, `let`, `subject`, `define_helper`; `tested_method :name` defines a `call_with(...)` helper that calls it on `subject`
- focus with `fdescribe`/`fcontext`/`ftest`/`fthey`, skip with `xdescribe`/`xcontext`/`xtest`/`xthey`
- assertions on `assert`: `equal!`, `empty!`, `includes!`, `includes_no!`, `raises!` (`lib/assertions.rb`)
- mocks: `a_mock { responding_to(:name) { always_returning value } }`, asserted with `was_called!`, `was_not_called!`, `received_call!` (`lib/mocks.rb`)

## Ruby that DragonRuby supports

DragonRuby runs mruby with `RUBY_VERSION` 3.0, and `.rubocop.yml` targets that. Checked in DragonRuby 6.58 and 7.24:

- Works: endless methods (but not with `yield`), `...` forwarding (also after leading arguments), `_1` and `it` block parameters, beginless ranges, `Hash#except`/`#slice`/`#transform_values`, `Array#filter_map`, `Enumerable#tally`, `clamp(min, max)`, `String#delete_prefix`, `Array#to_h` with a block
- Syntax errors: anonymous `&`/`*`/`**` forwarding, `{ x: }` hash shorthand, all pattern matching (`case/in`, `=>`, `x in Pattern`)
- Missing: `Array#intersect?`, `Array#sort_by!`, `Range#step`, `Hash#sum`, `Integer#digits`, `clamp(range)`, `rand(range)`, `Data`, `Struct.new(keyword_init: true)`
- Wrong without an error: `Integer#/` returns a Float (`7 / 2` is `3.5`, use `idiv`); `Hash#to_h` ignores its block and returns the hash unchanged; `send(name, *args, **{})` passes the empty hash as an extra positional argument; a keyword argument's default cannot use an earlier keyword argument (`def m(a:, b: a)` calls a method `a`); `module_function` without arguments does nothing (use `extend self`)

## Names the engine already uses

The top-level constants `Mat2`-`Mat4`, `Vec2`-`Vec4`, `Matrix`, `Geometry`, `Easing`, `Layout` and `Grid` belong to the engine (reopening `Mat3` as a module fails with "Mat3 is not a module"), and render targets cannot be named `:pixel` or `:solid`.

## Maintaining this template

Delete this section in games created from this template; it only applies to the `dragonruby-template` repository itself.

Tools for maintaining the template live on the orphan `maintenance` branch, so they do not come along into new games. After a DragonRuby update, run the Ruby support probe against the new release without checking the branch out:

```sh
git fetch origin maintenance
git show origin/maintenance:probe-ruby-support | bash -s -- <path to the DragonRuby release>
```

Then update "Ruby that DragonRuby supports" above and the disabled cops and `TargetRubyVersion` in `.rubocop.yml` to match.
