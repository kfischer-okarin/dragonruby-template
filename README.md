# My Game

## How to checkout the game
1. Extract the DragonRuby version you want to use somewhere
2. Delete original `mygame` folder (or alternatively rename it into `mygame-template` if you want to keep the files around)
3. Clone your game (this repository) via git
4. Copy the DragonRuby engine into your game repository (don't forget the hidden `.dragonruby` folder)

## How to update the DragonRuby version
1. Execute following command in your repository
   ```sh
   git clean -f -x -d
   ```
   This will recursively delete all unknown & ignored files in your repository (i.e. the engine).

   Be aware that this might also delete all other ignored files in your repository (like maybe save games) - so if you want
   to keep anything make sure that you backup those files first
2. Copy the new version of the DragonRuby engine into your game repository (don't forget the hidden `.dragonruby` folder)

## How to drive the running game from the shell
`scripts/game` starts its own instance of the game and controls it through the development web server (the port comes
from `webserver.port` in `mygame/metadata/cvars.txt`). Run it without arguments for the full list of commands.

```sh
scripts/game start              # or --headless: no window, but labels are missing from screenshots (not with shaders)
scripts/game press right a      # controller buttons, through the engine's input path
scripts/game wait-until 'Kernel.tick_count > 600'
scripts/game state
scripts/game screenshot menu/01-open
scripts/game pixel menu/01-open 640,360
scripts/game stop
```

By default it only controls the instance it started: if another process already listens on the port, `start` refuses and
leaves it alone. `doctor` also reports when the game has written `mygame/errors/last.txt` since the start.

To use a game you started yourself, put `--attach` before the command, e.g. `scripts/game --attach screenshot bug/01`.
Every command except `start` and `stop` works that way.

It needs `curl`, `jq`, `lsof` and `python3` (for `pixel`).

### Game hooks
The game can define an optional top-level `GameCli` module:

```ruby
module GameCli
  # Added to what `scripts/game state` prints
  def self.state
    { scene: $game.class.name }
  end

  # Called by `scripts/game reset <name>` after the game restarted from tick 0
  def self.setup(name)
    case name
    when :empty_level then $game.enemies.clear
    else raise "Unknown setup #{name}"
    end
  end
end
```
