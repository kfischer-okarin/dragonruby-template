# Render targets, blending and shaders in DragonRuby

Engine behavior that matters once a game draws into render targets, blends in more than one way, uses shaders or draws thousands of sprites per frame. Measured in DragonRuby 7.24; the engine's own docs do not cover it.

## Render targets

- Render targets render in the order the tick first touches them, so a target that draws another one has to be touched after it.
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
- `textures:` maps in order to `t1`, `t2`, ... Each texture needs a sampler with the same number, and every texture and sampler is declared with `space2`.
- `uniforms:` is a list of `{ type: :float, value: }` (or `:int`) that fills the `cbuffer` at `register(b0, space3)` in order. HLSL aligns `float4` fields to 16 bytes, so keep floats in groups of four that match the `float4` fields.
- Compile errors land in `mygame/errors/last.txt`. Saving the same shader twice within one second can leave the failed compile active: save or `touch` it again.
- On every boot the engine writes compiled `.dxil`, `.msl` and `.spv` files next to each shader (ignored by git).

## Sprites

- `r`, `g`, `b` and `a` are truncated to whole numbers and clamped to 0..255: `r: 100.9` draws as 100, `a: 0.75` as 0 (measured in 7.24 with `path: :pixel` sprites in a render target).

## Drawing thousands of sprites per frame

- Building a Hash with a dozen keys for every sprite every frame costs about 3 µs per sprite in mruby. Measured with 1,500 moving sprites: 7.4 ms of Ruby with Hashes, 2.5 ms with the alternative below.
- The alternative: an object with `draw_override(ffi)` that calls `ffi.draw_sprite_6` once per sprite with positional arguments, which costs about 0.35 µs per sprite.
  - The argument order is in the engine's `docs/oss/dragon/runtime/draw.rb`. In `blendmode_enum`, 1 blends and 2 adds.
  - Put the object into `outputs[...].sprites`, or give it a `primitive_marker` that returns `:sprite` to use `primitives`.
  - The engine's changelog says deprecating `draw_override` is under consideration, so keep it behind one class.
