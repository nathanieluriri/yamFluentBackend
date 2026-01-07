from string import Template

# --- Invitation Email Template ---
invitation_template_string = Template("""
<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html lang="en">
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=US-ASCII">
  <title>You are invited to ${portal_name}</title>
</head>
<body bgcolor="#f6f7fb" topmargin="0" leftmargin="0" marginheight="0" marginwidth="0" style="width: 100% !important; min-width: 100%; -webkit-font-smoothing: antialiased; -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; background-color: #f6f7fb; color: #1f2937; font-family: Helvetica, Arial, sans-serif; font-weight: normal; text-align: center; line-height: 20px; font-size: 14px; margin: 0; padding: 0;">
  <table class="body" style="border-spacing: 0; border-collapse: collapse; vertical-align: top; text-align: center; height: 100%; width: 100%; background-color: #f6f7fb; padding: 30px 0;" bgcolor="#f6f7fb">
    <tr style="vertical-align: top; text-align: center; padding: 0;" align="center">
      <td class="center" align="center" valign="top" style="word-break: break-word; -webkit-hyphens: auto; -moz-hyphens: auto; hyphens: auto; border-collapse: collapse !important; vertical-align: top; text-align: center; color: #1f2937; font-family: Helvetica, Arial, sans-serif; font-weight: normal; line-height: 20px; font-size: 14px; margin: 0; padding: 0;">
        <center style="width: 100%; min-width: 580px;">
          <table class="container" style="border-spacing: 0; border-collapse: collapse; vertical-align: top; text-align: inherit; width: 600px; margin: 0 auto; padding: 0;">
            <tr style="vertical-align: top; text-align: center; padding: 0;" align="center">
              <td style="word-break: break-word; -webkit-hyphens: auto; -moz-hyphens: auto; hyphens: auto; border-collapse: collapse !important; vertical-align: top; text-align: center; color: #1f2937; font-family: Helvetica, Arial, sans-serif; font-weight: normal; line-height: 20px; font-size: 14px; margin: 0; padding: 0;" align="center" valign="top">
                <table style="width: 100%; border-spacing: 0; border-collapse: collapse; background-color: #0f172a; border-radius: 10px 10px 0 0;">
                  <tr>
                    <td style="padding: 18px 24px; text-align: left; color: #ffffff; font-size: 16px; font-weight: bold; letter-spacing: 0.4px;">
                      ${portal_name}
                    </td>
                  </tr>
                </table>
                <table style="width: 100%; border-spacing: 0; border-collapse: collapse; background-color: #ffffff; border-radius: 0 0 10px 10px; border: 1px solid #e5e7eb; box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);">
                  <tr>
                    <td style="padding: 28px 30px 10px; text-align: left;">
                      <h1 style="margin: 0 0 12px; font-size: 24px; line-height: 28px; color: #0f172a; font-weight: 700;">Admin invitation</h1>
                      <p style="margin: 0 0 18px; font-size: 15px; line-height: 22px; color: #374151;">
                        You have been invited to join the admin workspace. Use the credentials below to sign in.
                      </p>
                    </td>
                  </tr>
                  <tr>
                    <td style="padding: 0 30px 10px; text-align: left;">
                      <table style="width: 100%; border-spacing: 0; border-collapse: collapse; background-color: #f8fafc; border: 1px solid #e5e7eb; border-radius: 8px;">
                        <tr>
                          <td style="padding: 12px 16px; font-size: 13px; text-transform: uppercase; letter-spacing: 1px; color: #64748b;">Inviter</td>
                          <td style="padding: 12px 16px; font-size: 14px; color: #0f172a; text-align: right;">${inviter_email}</td>
                        </tr>
                        <tr>
                          <td style="padding: 12px 16px; font-size: 13px; text-transform: uppercase; letter-spacing: 1px; color: #64748b; border-top: 1px solid #e5e7eb;">Invitee</td>
                          <td style="padding: 12px 16px; font-size: 14px; color: #0f172a; text-align: right; border-top: 1px solid #e5e7eb;">${invitee_email}</td>
                        </tr>
                      </table>
                    </td>
                  </tr>
                  <tr>
                    <td style="padding: 18px 30px 6px; text-align: left;">
                      <div style="font-size: 13px; color: #64748b; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Temporary password</div>
                      <div style="background-color: #f1f5ff; border: 1px solid #c7d2fe; border-radius: 8px; padding: 14px 16px; text-align: center;">
                        <div style="font-family: 'Courier New', Courier, monospace; font-size: 18px; letter-spacing: 1px; color: #1e293b; background-color: #ffffff; border: 1px dashed #93c5fd; border-radius: 6px; padding: 10px 12px; display: inline-block; user-select: all;">${invitee_password}</div>
                        <div style="margin-top: 8px; font-size: 12px; color: #6b7280;">Tip: click and drag to copy.</div>
                      </div>
                    </td>
                  </tr>
                  <tr>
                    <td style="padding: 12px 30px 22px; text-align: left;">
                      <p style="margin: 0 0 6px; font-size: 14px; line-height: 20px; color: #374151;">
                        Please sign in with your email and the password above, then change it immediately.
                      </p>
                      <p style="margin: 0; font-size: 12px; line-height: 18px; color: #6b7280;">
                        If you were not expecting this invitation, you can ignore this email.
                      </p>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
          </table>
        </center>
      </td>
    </tr>
  </table>
</body>
</html>
""")

def generate_invitation_email_from_template(
    invitee_email: str,
    inviter_email: str,
    invitee_password: str,
    portal_name: str = "Yam Fluent Admin Portal"
) -> str:
    """
    Generates an invitation email from a template, handling potential errors.
    """
    try:
        return invitation_template_string.substitute(
            invitee_email=invitee_email,
            inviter_email=inviter_email,
            invitee_password=invitee_password,
            portal_name=portal_name
        )
    except KeyError as e:
        print(f"Error: Missing template variable: {e}")
        return None
