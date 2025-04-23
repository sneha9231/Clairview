```mermaid
flowchart TD
    Project["cloned_repo"]
    dir_awesome_md["awesome.md"]
    dir_code_of_conduct_md["code-of-conduct.md"]
    dir_contributing_md["contributing.md"]
    dir_create_list_md["create-list.md"]
    dir_license["license"]
    dir_media["📁 media"]
    dir_media_badge_flat_svg["badge-flat.svg"]
    dir_media_badge_flat2_svg["badge-flat2.svg"]
    dir_media_badge_ai["badge.ai"]
    dir_media_badge_svg["badge.svg"]
    dir_media_logo_ai["logo.ai"]
    dir_media_logo_png["logo.png"]
    dir_media_logo_svg["logo.svg"]
    dir_media_mentioned_badge_flat_svg["mentioned-badge-flat.svg"]
    dir_media_mentioned_badge_sketch["mentioned-badge.sketch"]
    dir_media_mentioned_badge_svg["mentioned-badge.svg"]
    dir_media_readme_md["readme.md"]
    dir_media_social_preview_png["social-preview.png"]
    dir_media --> dir_media_badge_flat_svg
    dir_media --> dir_media_badge_flat2_svg
    dir_media --> dir_media_badge_ai
    dir_media --> dir_media_badge_svg
    dir_media --> dir_media_logo_ai
    dir_media --> dir_media_logo_png
    dir_media --> dir_media_logo_svg
    dir_media --> dir_media_mentioned_badge_flat_svg
    dir_media --> dir_media_mentioned_badge_sketch
    dir_media --> dir_media_mentioned_badge_svg
    dir_media --> dir_media_readme_md
    dir_media --> dir_media_social_preview_png
    dir_pull_request_template_md["pull_request_template.md"]
    dir_readme_md["readme.md"]
    Project --> dir_awesome_md
    Project --> dir_code_of_conduct_md
    Project --> dir_contributing_md
    Project --> dir_create_list_md
    Project --> dir_license
    Project --> dir_media
    Project --> dir_pull_request_template_md
    Project --> dir_readme_md
```