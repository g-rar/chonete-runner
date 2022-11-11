from bot import bot
import random
from interactions import CommandContext, Option, OptionType, SelectMenu, \
    SelectOption, Component, Embed, ComponentContext, Message, EmbedField
import srcomapi
import srcomapi.datatypes as src_dt
from datetime import datetime
from interactions.ext.wait_for import wait_for_component
from asyncio.exceptions import TimeoutError
from pprint import pformat
from testConsts import testPlayer
import os

sr_api = srcomapi.SpeedrunCom(api_key=os.getenv("SCROM_API_KEY"))
sr_api.debug = 1


def generateId(id: str):
    return id + str('%030x' % random.randrange(16**30))


@bot.command(
    name="saludar",
    description="pa' saludar a todo el mundo :D:D",
)
async def saludar(ctx: CommandContext):
    await ctx.send(f"Hola, {ctx.member.name}!")


@bot.command(
    name="buscar_en_categoria",
    description="Buscar en una cateogria jugadores ticos",
    options=[
        Option(name="juego", description="Nombre o así del Juego para buscar",
                type=OptionType.STRING, required=True)
    ]
)
async def buscarEnCategoria(ctx: CommandContext, juego: str):
    games = sr_api.search(src_dt.Game, {"name": juego})
    # having this as a dictionary would be useful

    if len(games) == 0:
        await ctx.send(f"No encontré juegos con `{juego}` 🤷‍♂️")
        return

    # TODO add if there's only one game
    games_com = SelectMenu(
        custom_id=generateId("games_search_"),
        options=[
            SelectOption(label=game.name, value=game.abbreviation)
            for game in games
        ],
        placeholder="Elegí el juego en el que querés buscar"
    )
    games_select_msg = await ctx.send(components=games_com)
    gameSelectCtx = await wait_component_with_custom_id(games_com, games_select_msg)
    if not gameSelectCtx:
        return
    gameAbb = gameSelectCtx.data.values[0]
    game: src_dt.Game = next(
        filter(lambda g: g.abbreviation == gameAbb, games))

    await ctx.edit(f"Elegiste el juego `{game.name}`", components=[])

    cats_by_type = {}
    for cat in game.categories:
        # do I like this?
        cats_by_type\
            .setdefault(cat.type, [])\
            .append(cat)

    # TODO make it so that you can choose the category type
    # if 'per-level' in cats_by_type and 'per-game' in cats_by_type:
    #     type_select_msg = await ctx.channel.send("¿Qué tipo de categoría buscás?",
    #         components=[
    #             Button(style=ButtonStyle.PRIMARY, )
    #         ]
    #     )
    if 'per-game' not in cats_by_type:
        await games_select_msg.reply("No hay categorías por juego para ese juego. Sería solo por nivel \n"
                                     "Eso no lo manejo ahorita jefe, vuelva después 🤷‍♂️")
        return

    cat_select = SelectMenu(
        custom_id=generateId("category_select_"),
        placeholder="Elegí la categoría del juego en la que querés buscar",
        options=[
            SelectOption(label=cat.name, value=cat.id)
            for cat in cats_by_type['per-game']
        ]
    )
    cat_select_msg = await games_select_msg.reply(components=cat_select)
    cat_select_ctx = await wait_component_with_custom_id(cat_select, cat_select_msg)
    if not cat_select_ctx:
        return

    category_id = cat_select_ctx.data.values[0]
    category: src_dt.Category = next(filter(
        lambda c: c.id == category_id,
        cats_by_type['per-game']
    ))

    await cat_select_ctx.edit(f"Voy a buscar en la categoría `{category.name}`", components=[])

    leaderBoard = src_dt.Leaderboard(sr_api, data=sr_api.get(
        f"leaderboards/{game.id}/category/{category_id}?embed=players"))
    playersData = leaderBoard.players['data']

    def isCostarrican(player: dict):
        if not player.get('location'):
            player['location'] = {}
        return 'cr' == player\
            .get('location', {})\
            .get('country', {})\
            .get('code', '')

    costarricanPlayers = list(filter(isCostarrican, playersData))

    if len(costarricanPlayers) == 0:
        await cat_select_msg.reply("No encontré jugadores costarricenses para esa categoría 🤷‍♂️")
        return

    await cat_select_msg.reply("Se encontraron estos jugadores:")
    try:
        await cat_select_msg.reply(embeds=[
            getPlayerEmbed(cr_p)
            for cr_p in costarricanPlayers
        ])
    except:
        await cat_select_msg.reply(f'''py\n{pformat(costarricanPlayers)}''')


# @bot.command(
#     name="test_embed",
#     description="Para hacerlo bonito"
# )
# async def testPlayerEmbed(ctx: CommandContext):
#     playerEmbed = getPlayerEmbed(testPlayer)
#     await ctx.send(embeds=[playerEmbed, playerEmbed])

########################################################
###############  Utility Functions  ####################
########################################################


def formatDate(d: str):
    t = int(datetime.strptime(d, '%Y-%m-%dT%H:%M:%SZ').timestamp())
    return f"<t:{t}:f>"


def getPlayerEmbed(p: dict):
    if not p.get('location'):
        p['location'] = {'country': {'names': {'international': None}}}
    player_name = p.get('names', {}).get('international', '[Anon]')
    embed = Embed(
        title=player_name,
        url=p['weblink'],
        fields=[
            EmbedField(
                name="Localización",
                value=p['location']['country']['names']['international'] or "??",
                inline=True
            ),
            EmbedField(
                name="Fecha de ingreso",
                value="N/A" if not p['signup'] else formatDate(p['signup']),
                inline=True
            ),
            EmbedField(
                name="Rol",
                value=p.get('role', 'N/A').capitalize(),
                inline=True
            )
        ]
    )
    srcom_links = {
        'games': 'Juegos',
        'runs': 'Runs',
        'personal-bests': 'PBs',
    }
    srcom_links_str = ""
    for l in p['links']:
        if l['rel'] in srcom_links:
            srcom_links_str += \
                f" [[ {srcom_links[l['rel']]} ]]({l['uri']})  "

    embed.add_field(name="Enlaces de SCR:",
                    value=srcom_links_str, inline=False)

    media_links = {'twitch': 'Twitch',
                   'twitter': 'Twitter', 'youtube': 'YouTube'}
    media_links_str = ""

    for k, v in media_links.items():
        if p[k] is not None:
            media_links_str += \
                f"- {v}: {p[k]['uri']}\n"

    if media_links_str:
        embed.add_field(name="Redes:", value=media_links_str, inline=False)

    if (thumbnail := p.get('assets', {}).get('image', {}).get('uri')):
        embed.set_thumbnail(url=thumbnail)
    if (icon := p.get('assets', {}).get('icon', {}).get('uri')):
        embed.set_footer(player_name,icon_url=icon)

    return embed


async def wait_component_with_custom_id(comp: Component, msg: Message) -> ComponentContext | None:
    try:
        cctx: ComponentContext = await wait_for_component(
            bot=bot,
            components=comp,
            check=lambda sctx: sctx.custom_id == comp.custom_id,
            timeout=60
        )
        return cctx
    except TimeoutError:
        await msg.disable_all_components()
        await msg.create_reaction('⏰')
        await msg.create_reaction('❌')


def main():
    bot.start()


if __name__ == '__main__':
    main()
