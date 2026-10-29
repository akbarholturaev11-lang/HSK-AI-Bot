# Android widget: illustration and text need separate space

- Cause: a full-frame illustration leaves no safe text area. Removing a dark panel or moving overlay text upward still covers the face. A later failed render can also leave older PNGs in the same test directory.
- Fix: allocate disjoint header/art cells, keep the selected modern transparent panda's aspect ratio, and share the actual native rounded header with the install preview. Use semantic high-contrast colors; no scrim or scene overlay.
- Risk: very small sizes and font metrics can clip captions. Decorative outline copies are not additional semantic text; hidden copies must not be counted as visible clipping.
- Prevention: `WidgetPersonalLayoutTest` measures visible localized text and real panda rectangles at all three sizes/themes, asserts no intersection and verifies the actual counter/font. Use a fresh `widgetQaOutput` per run, require the final successful result and inspect only PNGs from that run. Legacy wording may use its existing max-lines ellipsis; real personal copy has its own non-truncation guard.
