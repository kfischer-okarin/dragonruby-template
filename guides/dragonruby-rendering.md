# Render targets, blending and shaders in DragonRuby

Engine behavior that matters once a game draws into render targets, blends in more than one way, uses shaders or draws thousands of sprites per frame. Measured in DragonRuby 7.24; the engine's own docs do not cover it.

## Render targets

- Render targets render in the order the tick first touches them, so a target that draws another one has to be touched after it.
- `:pixel` and `:solid` are reserved names; using them raises.
- Alpha blending into a target cleared to transparent stores the color premultiplied:
  - the RGB is already multiplied by alpha;
  - alpha accumulates as `src + dst × (1 - src)`.

  Drawing that target again with normal blending multiplies by alpha a second time, which darkens soft edges. Copy it with `blendmode_enum: 0`, or divide the RGB by alpha in a shader.
- **Additive targets have zero alpha.** Additive blending (`blendmode_enum: 2`) adds color but leaves the target's alpha alone, so on a target cleared to transparent the alpha stays 0.
  - Drawing such a target into another one adds nothing, with any blend mode, because blending multiplies by that alpha. A glow or light layer composed this way silently disappears.
  - Workaround: read the target in a shader as a texture (shaders take its RGB as it is).
  - Workaround: clear the target to opaque black (`[0, 0, 0, 255]`), so its alpha is 1 and black adds nothing. This follows from the same measurement but was not measured itself.

## Shaders

- They need `shaders=true` in `mygame/metadata/game_metadata.txt` and the Pro license, and they cannot run headless (see CLAUDE.md). The publisher warns that `scale_quality=3` (pixel art) does not work with shaders.
- The API is `outputs[:target].shader = { path:, textures:, uniforms: }`, or `outputs.shader` for the screen. The engine's `samples/14_shaders` shows it; `docs/api/outputs.md` still describes an older GLSL API that no longer applies.
- Every `.hlsl` file has to be required, like a Ruby file, before it is used.
- A shader on a render target runs once over the whole target after its primitives are drawn, with the result as `t0`. It does not run per primitive.
- `textures:` maps in order to `t1`, `t2`, ... Each texture needs a sampler with the same number, and every texture and sampler is declared with `space2`.
- `uniforms:` is a list of `{ type: :float, value: }` (or `:int`) that fills the `cbuffer` at `register(b0, space3)` in order. HLSL aligns `float4` fields to 16 bytes, so keep floats in groups of four that match the `float4` fields.
- Compile errors land in `mygame/errors/last.txt`. Saving the same shader twice within one second can leave the failed compile active: save or `touch` it again.
- On every boot the engine writes compiled `.dxil`, `.msl` and `.spv` files next to each shader (ignored by git).

## Drawing thousands of sprites per frame

- Building a Hash with a dozen keys for every sprite every frame costs about 3 µs per sprite in mruby. Measured with 1,500 moving sprites: 7.4 ms of Ruby with Hashes, 2.5 ms with the alternative below.
- The alternative: an object with `draw_override(ffi)` that calls `ffi.draw_sprite_6` once per sprite with positional arguments, which costs about 0.35 µs per sprite.
  - The argument order is in the engine's `docs/oss/dragon/runtime/draw.rb`. In `blendmode_enum`, 1 blends and 2 adds.
  - Put the object into `outputs[...].sprites`, or give it a `primitive_marker` that returns `:sprite` to use `primitives`.
  - The engine's changelog says deprecating `draw_override` is under consideration, so keep it behind one class.
