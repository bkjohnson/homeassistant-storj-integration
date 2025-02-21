# Storj

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![pre-commit][pre-commit-shield]][pre-commit]
[![Black][black-shield]][black]

[![hacs][hacsbadge]][hacs]
[![Project Maintenance][maintenance-shield]][user_profile]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

[![Discord][discord-shield]][discord]
[![Community Forum][forum-shield]][forum]

This integration allows you to connect your [Storj][storj] account with Home Assistant Backups. When you set up this integration, you will have a new folder called `backups` in the given bucket where all the backups will be stored.

## Prerequisites

You need to have a Storj account along with an [Access Grant that you created][access-grant]. The [`uplink` CLI tool][uplink] will also need to be installed on your Home Assistant instance.

## Installation

You only need one of these installation options.

### Manually

If you've cloned the repo, you can symlink to it.

```
cd <home_assistant_config_directory>/custom_components/
ln -s path/to/cloned/repo storj
```

Alternatively, place the `storj` directory into:

```yaml
<home_assistant_config_directory>/custom_components/
```

Next, search for "Storj" from the integrations page and proceed with the configuration.

[![Open your integrations dashboard on your Home Assistant instance](https://my.home-assistant.io/badges/integrations.svg)](https://my.home-assistant.io/redirect/integrations/)

### Via [HACS](https://hacs.xyz/)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=bkjohnson&repository=homeassistant-storj-integration&category=integration)

## Configuration is done in the UI

<!---->

## Development Setup

1. Install dependencies
   ```
   pip install -r requirements.txt
   ```

## Contributions are welcome!

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)

## Credits

This project was generated from [@oncleben31](https://github.com/oncleben31)'s [Home Assistant Custom Component Cookiecutter](https://github.com/oncleben31/cookiecutter-homeassistant-custom-component) template.

Code template was mainly taken from [@Ludeeus](https://github.com/ludeeus)'s [integration_blueprint][integration_blueprint] template

---

[access-grant]: https://storj.dev/dcs/access#create-access-grant
[integration_blueprint]: https://github.com/custom-components/integration_blueprint
[black]: https://github.com/psf/black
[black-shield]: https://img.shields.io/badge/code%20style-black-000000.svg?style=for-the-badge
[buymecoffee]: https://www.buymeacoffee.com/bkjohnson
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=for-the-badge
[commits-shield]: https://img.shields.io/github/commit-activity/y/bkjohnson/homeassistant-storj-integration.svg?style=for-the-badge
[commits]: https://github.com/bkjohnson/homeassistant-storj-integration/commits/main
[hacs]: https://hacs.xyz
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[discord]: https://discord.gg/Qa5fW2R
[discord-shield]: https://img.shields.io/discord/330944238910963714.svg?style=for-the-badge
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license-shield]: https://img.shields.io/github/license/bkjohnson/homeassistant-storj-integration.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-%40bkjohnson-blue.svg?style=for-the-badge
[pre-commit]: https://github.com/pre-commit/pre-commit
[pre-commit-shield]: https://img.shields.io/badge/pre--commit-enabled-brightgreen?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/bkjohnson/homeassistant-storj-integration.svg?style=for-the-badge
[releases]: https://github.com/bkjohnson/homeassistant-storj-integration/releases
[storj]: https://www.storj.io
[uplink]: https://storj.dev/dcs/api/uplink-cli/installation
[user_profile]: https://github.com/bkjohnson
