# dragonruby-template maintenance

Tools for maintaining the template itself. They live on this orphan branch so that games created from the template do not
get them.

## probe-ruby-support

Checks which Ruby syntax and core methods a DragonRuby release supports by evaluating small snippets in a throwaway game:

```sh
./probe-ruby-support <path to the DragonRuby release>
```

Run it without checking this branch out:

```sh
git fetch origin maintenance
git show origin/maintenance:probe-ruby-support | bash -s -- <path to the DragonRuby release>
```

Use the results to update "Ruby that DragonRuby supports" in the template's `CLAUDE.md` and the cops in `.rubocop.yml`.
