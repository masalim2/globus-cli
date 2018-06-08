import click
import uuid

from globus_cli.helpers import (
    is_remote_session, do_link_auth_flow, do_local_server_auth_flow)
from globus_cli.safeio import safeprint
from globus_cli.services.auth import get_auth_client, maybe_lookup_identity_id
from globus_cli.parsing import common_options, no_local_server_option


@click.command('boost',
               short_help=("Boost your CLI auth session"),
               help=("Boost your current CLI auth session by authenticating "
                     "with specific identities."))
@common_options(no_format_option=True, no_map_http_status_option=True)
@no_local_server_option
@click.argument('identities', nargs=-1, required=False)
@click.option('--all', is_flag=True,
              help='authenticate with every identity in your identity set')
def session_boost(identities, no_local_server, all):

    if (not (identities or all)) or (identities and all):
        raise click.UsageError(
            'Either give one or more IDENTITIES or use --all')

    # if --all use every identity id in the user's identity set
    if all:
        auth_client = get_auth_client()
        res = auth_client.oauth2_userinfo()
        try:
            identity_ids = [user["sub"] for user in res["identity_set"]]
        except KeyError:
            safeprint("Your current login does not have the consents required "
                      "to view your full identity set. Please log in again "
                      "to agree to the required consents.",
                      write_to_stderr=True)
            click.get_current_context().exit(1)

    # otherwise try to resolve any non uuid values to identity ids
    else:
        identity_ids = []
        for val in identities:
            try:
                uuid.UUID(val)
                identity_ids.append(val)
            except ValueError:
                try:
                    maybe_id = maybe_lookup_identity_id(val)
                    uuid.UUID(maybe_id)
                    identity_ids.append(maybe_id)
                except (ValueError, TypeError):
                    safeprint("No such identity {}".format(val),
                              write_to_stderr=True)
                    click.get_current_context().exit(1)

    session_params = {
        "session_required_identities": ",".join(identity_ids),
        "session_message": "Authenticate to boost your CLI session.",
        "prompt": "login"
    }

    # use a link login if remote session or user requested
    if no_local_server or is_remote_session():
        do_link_auth_flow(session_params=session_params)

    # otherwise default to a local server login flow
    else:
        safeprint(
            "You are running 'globus session bost', "
            "which should automatically open a browser window for you to "
            "authenticate with specific identities.\n"
            "If this fails or you experience difficulty, try "
            "'globus session boost --no-local-server'"
            "\n---")
        do_local_server_auth_flow(session_params=session_params)

    safeprint("\nYou have successfully boosted your CLI session.\n"
              "Use 'globus session show' to see the updated session.")
