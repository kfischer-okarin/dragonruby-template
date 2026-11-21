# Render targets, blending and shaders in DragonRuby

Engine behavior that matters once a game draws into render targets, blends in more than one way, uses shaders or pixel arrays, or draws thousands of sprites per frame. Measured in DragonRuby 7.24; the engine's own docs do not cover it.

## Render targets

- Render targets render in the order the tick first touches them, so a target that draws another one has to be touched after it.
- A target keeps its pixels until a tick accesses it through `outputs[...]` again, so something that does not change can be drawn into a target once and then drawn from it every tick. Any access clears it for that tick, also one that only sets its `shader=`. Measured in 7.24: a target drawn into once still showed its content 60 ticks later, and one whose `outputs[...]` was merely accessed every tick showed nothing.
- `:pixel` and `:solid` are reserved names; using them raises.
- Alpha blending into a target cleared to transparent stores the color premultiplied:
  - the RGB is already multiplied by alpha;
  - alpha accumulates as `src + dst × (1 - src)`.

  Drawing that target again with normal blending multiplies by alpha a second time, which darkens soft edges. Draw it with a premultiplied blend mode instead, which keeps its transparency (measured in 6.58 and 7.24: a 50% red shows correctly over black and white):

  ```ruby
  PREMULTIPLIED_BLENDMODE = Numeric.compose_blendmode(BLENDFACTOR_ONE, BLENDFACTOR_ONE_MINUS_SRC_ALPHA, BLENDOPERATION_ADD,
                                                      BLENDFACTOR_ONE, BLENDFACTOR_ONE_MINUS_SRC_ALPHA, BLENDOPERATION_ADD)
  { path: :target, blendmode: PREMULTIPLIED_BLENDMODE }
  ```

  Or copy it with `blendmode_enum: 0` (drops its transparency), or divide the RGB by alpha in a shader.
- A blend mode from `Numeric.compose_blendmode` has to go in `blendmode:`. In `blendmode_enum:` it blends like normal alpha blending, without an error.
- This blend mode multiplies what is already there by the sprite's color and leaves the destination's alpha alone:

  ```ruby
  MULTIPLY_BLENDMODE = Numeric.compose_blendmode(BLENDFACTOR_DST_COLOR, BLENDFACTOR_ONE_MINUS_SRC_ALPHA, BLENDOPERATION_ADD,
                                                 BLENDFACTOR_ZERO, BLENDFACTOR_ONE, BLENDOPERATION_ADD)
  ```

  It computes `src × dst + dst × (1 - src alpha)`, and the sprite's color is not premultiplied by its alpha. Measured in 7.24 over gray `(128, 128, 128)`: an opaque sprite with the color `(128, 255, 64)` gives `(64, 128, 32)`, but the same sprite with alpha 128 gives `(128, 192, 96)`, brighter than the gray. To multiply by `tint` with a strength `a`, give the sprite the color `tint × a` and the alpha `a` (in Ruby, or as a shader's output), which gives `dst × lerp(1, tint, a)`. Drawn into a target cleared to transparent, it leaves the target transparent.
- **Additive targets have zero alpha.** Additive blending (`blendmode_enum: 2`) adds color but leaves the target's alpha alone, so on a target cleared to transparent the alpha stays 0.
  - Drawing such a target into another one adds nothing, with any blend mode, because blending multiplies by that alpha. A glow or light layer composed this way silently disappears.
  - Workaround: read the target in a shader as a texture (shaders take its RGB as it is).
  - Workaround: clear the target to opaque black (`[0, 0, 0, 255]`), so its alpha is 1 and black adds nothing. Measured in 6.58 and 7.24: additive red drawn into it and then drawn additively over gray `(64, 64, 64)` shows `(255, 64, 64)`.

## Shaders

- They need `shaders=true` in `mygame/metadata/game_metadata.txt` and the Pro license, and they cannot run headless (see CLAUDE.md). The publisher warns that `scale_quality=3` (pixel art) does not work with shaders.
- The API is `outputs[:target].shader = { path:, textures:, uniforms: }`, or `outputs.shader` for the screen. The engine's `samples/14_shaders` shows it; `docs/api/outputs.md` still describes an older GLSL API that no longer applies.
- Every `.hlsl` file has to be required, like a Ruby file, before it is used.
- A shader on a render target does not change the target. It is the fragment shader of every sprite that draws the target, so it runs for every pixel that sprite covers, wherever the target is drawn, and not per primitive drawn into the target.
  - `t0` is the target, `TEXCOORD0` the sprite's texture coordinate (with 0, 0 at the target's top left) and `COLOR0` the sprite's color; the sprite's `scale_quality_enum` and `blendmode_enum` apply.
  - Measured in 7.24 with a shader on a 160×90 target that reads a 320×180 target through `textures:` and ignores `COLOR0`: drawn at 1280×720, it showed the 320×180 target's full detail inside the 160×90 target's pixels, and a sprite with `r: 0` did not tint it.
- The shader applies only in a tick that sets it. A target kept from an earlier tick (see Render targets) is drawn without the shader it had then, and setting `shader=` again clears it. To draw something cached through a shader, keep it in a plain target and draw that every tick into a second target that has the shader. Measured in 7.24: a target drawn into with a shader in one tick showed its plain content when drawn in later ticks.
- `textures:` maps in order to `t1`, `t2`, ... Each texture needs a sampler with the same number, and every texture and sampler is declared with `space2`.
- `uniforms:` is a list of `{ type: :float, value: }` (or `:int`) that fills the `cbuffer` at `register(b0, space3)` in order. HLSL aligns `float4` fields to 16 bytes, so keep floats in groups of four that match the `float4` fields.
- Compile errors land in `mygame/errors/last.txt`. Saving the same shader twice within one second can leave the failed compile active: save or `touch` it again.
- On every boot the engine writes compiled `.dxil`, `.msl` and `.spv` files next to each shader (ignored by git).

## Pixel arrays

- `args.pixel_array(name).pixels` holds one integer per pixel with red in the lowest byte: `0xAABBGGRR`. Measured in 7.24: `0xFF0000FF` is opaque red and `0xFFFF0000` opaque blue. The engine's `samples/07_advanced_rendering/06_pixel_arrays` only uses green, which reads the same in either order.

## Sprites

- `r`, `g`, `b` and `a` are truncated to whole numbers and clamped to 0..255: `r: 100.9` draws as 100, `a: 0.75` as 0 (measured in 7.24 with `path: :pixel` sprites in a render target).

## Drawing thousands of sprites per frame

- Building a Hash with a dozen keys for every sprite every frame costs about 3 µs per sprite in mruby. Measured with 1,500 moving sprites: 7.4 ms of Ruby with Hashes, 2.5 ms with the alternative below.
- The alternative: an object with `draw_override(ffi)` that calls `ffi.draw_sprite_6` once per sprite with positional arguments, which costs about 0.35 µs per sprite.
  - The argument order is in the engine's `docs/oss/dragon/runtime/draw.rb`. In `blendmode_enum`, 1 blends and 2 adds.
  - Put the object into `outputs[...].sprites`, or give it a `primitive_marker` that returns `:sprite` to use `primitives`.
  - The engine's changelog says deprecating `draw_override` is under consideration, so keep it behind one class.
