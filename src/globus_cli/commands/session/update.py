import click

from globus_cli.helpers import (
    do_link_auth_flow,
    do_local_server_auth_flow,
    is_remote_session,
)
from globus_cli.parsing import IdentityType, command, no_local_server_option
from globus_cli.services.auth import get_auth_client


def _update_session_params_all_case(identity_set, session_params):
    """if --all use every identity id in the user's identity set"""
    identity_ids = [x["sub"] for x in identity_set]
    # set session params once we have all identity ids
    session_params["session_required_identities"] = ",".join(identity_ids)


def _update_session_params_identities_case(identity_set, session_params, identities):
    """
    given a set of identities (which must be either a mix of usernames and IDs or a list
    of domains), use that to update the session as appropriate
    """
    identity_ids = [i.value for i in identities if i.idtype == "identity"]
    identity_usernames = [i.value for i in identities if i.idtype == "username"]
    identity_domains = [i.value for i in identities if i.idtype == "domain"]

    if identity_domains and (identity_ids or identity_usernames):
        raise click.UsageError(
            "domain-type identities and user-type identities are mutually exclusive"
        )

    # track if we find any identity IDs not in the user's identity set
    any_ids_not_in_set = False
    id_set_ids = {x["sub"] for x in identity_set}
    id_set_mapping = {x["username"]: x["sub"] for x in identity_set}

    # check Identity IDs first, since we'll expand this list with names next
    # we don't wnat to check usernames twice
    for identity_id in identity_ids:
        if identity_id not in id_set_ids:
            click.echo(f"'{identity_id}' is not in your identity set", err=True)
            any_ids_not_in_set = True

    # if usernames were used, fetch the identity set and pull identity IDs from there
    # do not use 'get_identities' as it will easily return identities which are not in
    # your identity set
    if identity_usernames:
        for name in identity_usernames:
            try:
                identity_ids.append(id_set_mapping[name])
            except KeyError:
                click.echo(f"'{name}' is not in your identity set", err=True)
                any_ids_not_in_set = True

    if any_ids_not_in_set:
        click.get_current_context().exit(1)

    # update session params once we have resolved usernames (if necessary)
    if identity_ids:
        session_params["session_required_identities"] = ",".join(identity_ids)
    else:
        # "single domain" may be counterintuitive since we may be sending multiple
        # domains, but it is the correct parameter
        session_params["session_required_single_domain"] = ",".join(identity_domains)


@command(
    "update",
    short_help="Update your CLI auth session",
    disable_options=["format", "map_http_status"],
)
@no_local_server_option
@click.argument(
    "identities", type=IdentityType(allow_domains=True), nargs=-1, required=False
)
@click.option(
    "--all",
    is_flag=True,
    help="Add every identity in your identity set to your session",
)
def session_update(identities, no_local_server, all):
    """
    Update your current CLI auth session by authenticating
    with specific identities.

    This command starts an authentication flow with Globus Auth similarly to
    'globus login' but specifies which identities to authenticate with.

    After successful authentication, the user's CLI auth session will be updated
    with any new identities and current Auth Times.

    Identity values may be identity IDs, identity usernames, or domains. Domains are
    mutually exclusive with IDs and usernames.
    When usernames or IDs are used, they must be in your identity set.
    """

    if (not (identities or all)) or (identities and all):
        raise click.UsageError("IDENTITY values and --all are mutually exclusive")

    auth_client = get_auth_client()
    session_params = {"session_message": "Authenticate to update your CLI session."}
    identity_set = auth_client.oauth2_userinfo()["identity_set"]

    if all:
        _update_session_params_all_case(identity_set, session_params)
    else:
        _update_session_params_identities_case(identity_set, session_params, identities)

    # use a link login if remote session or user requested
    if no_local_server or is_remote_session():
        do_link_auth_flow(session_params=session_params)

    # otherwise default to a local server login flow
    else:
        click.echo(
            "You are running 'globus session update', "
            "which should automatically open a browser window for you to "
            "authenticate with specific identities.\n"
            "If this fails or you experience difficulty, try "
            "'globus session update --no-local-server'"
            "\n---"
        )
        do_local_server_auth_flow(session_params=session_params)

    click.echo(
        "\nYou have successfully updated your CLI session.\n"
        "Use 'globus session show' to see the updated session."
    )
