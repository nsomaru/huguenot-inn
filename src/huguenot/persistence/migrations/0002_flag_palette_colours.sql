-- Global counsel-bundle flag palette.
-- depends: 0001_initial

CREATE TABLE IF NOT EXISTS flag_palette_colours (
    id INTEGER PRIMARY KEY,
    display_order INTEGER NOT NULL UNIQUE CHECK (display_order >= 1),
    colour_hex TEXT NOT NULL UNIQUE CHECK (
        length(colour_hex) = 7
        AND colour_hex GLOB '#[0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f]'
    ),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO flag_palette_colours(display_order, colour_hex)
SELECT display_order, colour_hex
FROM (
    SELECT 1 AS display_order, '#3467A5' AS colour_hex
    UNION ALL SELECT 2, '#71B735'
    UNION ALL SELECT 3, '#F4DC05'
    UNION ALL SELECT 4, '#F13958'
    UNION ALL SELECT 5, '#FE6F25'
    UNION ALL SELECT 6, '#669EAF'
    UNION ALL SELECT 7, '#FF646B'
    UNION ALL SELECT 8, '#CD638B'
)
WHERE NOT EXISTS (SELECT 1 FROM flag_palette_colours);
