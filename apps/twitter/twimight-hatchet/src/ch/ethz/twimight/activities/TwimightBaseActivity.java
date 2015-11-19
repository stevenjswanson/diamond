/*******************************************************************************
 * Copyright (c) 2011 ETH Zurich.
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the GNU Public License v2.0
 * which accompanies this distribution, and is available at
 * http://www.gnu.org/licenses/old-licenses/gpl-2.0.html
 * 
 * Contributors:
 *     Paolo Carta - Implementation
 *     Theus Hossmann - Implementation
 *     Dominik Schatzmann - Message specification
 ******************************************************************************/
package ch.ethz.twimight.activities;

import java.util.Observable;
import java.util.Observer;

import android.app.ActionBar;
import android.app.AlertDialog;
import android.content.ContentResolver;
import android.content.DialogInterface;
import android.content.Intent;
import android.content.res.Resources;
import android.database.Cursor;
import android.graphics.drawable.Drawable;
import android.net.Uri;
import android.os.AsyncTask;
import android.os.Bundle;
import android.preference.PreferenceManager;
import android.support.v4.app.FragmentActivity;
import android.util.Log;
import android.view.Menu;
import android.view.MenuInflater;
import android.view.MenuItem;
import android.view.View;
import android.view.ViewGroup;
import android.view.Window;
import android.widget.TextView;
import android.widget.Toast;
import ch.ethz.twimight.R;
import ch.ethz.twimight.net.twitter.Tweets;
import ch.ethz.twimight.net.twitter.TwitterService;
import ch.ethz.twimight.net.twitter.TwitterUsers;
import ch.ethz.twimight.util.Constants;

/**
 * The base activity for all Twimight activities.
 * 
 * @author thossmann
 * 
 */
public abstract class TwimightBaseActivity extends FragmentActivity implements
		Observer {

	static TwimightBaseActivity instance;
	private static final String TAG = "TwimightBaseActivity";
	public static final boolean D = true;

	ActionBar actionBar;
	static Drawable dd, dn;

	private View bottomStatusBar;
	private TextView tvNeighborCount;
	private TextView tvStatus;

	/**
	 * Called when the activity is first created.
	 */
	@Override
	public void onCreate(Bundle savedInstanceState) {
		super.onCreate(savedInstanceState);

		requestWindowFeature(Window.FEATURE_INDETERMINATE_PROGRESS);

		// action bar
		actionBar = getActionBar();
		actionBar.setHomeButtonEnabled(true);
		actionBar.setDisplayShowTitleEnabled(true);
		actionBar.setTitle("@" + LoginActivity.getTwitterScreenname(this));		

	}

	/**
	 * on Resume
	 */
	@Override
	public void onResume() {
		super.onResume();
		instance = this;
		
		if(dd == null || dn == null) {
			Log.i(TAG,"loading action bar backgrounds");
			Resources resources = getResources();
			dd = resources.getDrawable(R.drawable.top_bar_background_disaster);
			dn = resources.getDrawable(R.drawable.top_bar_background);
		}	
		
		// bottom status bar (can't do it in onCreate because layout is not set yet)
		bottomStatusBar = findViewById(R.id.bottomStatusBar);
		tvNeighborCount = (TextView) findViewById(R.id.tvNeighborCount);
		tvStatus = (TextView) findViewById(R.id.tvStatus);
		
		actionBar.setBackgroundDrawable(dn);
		Log.i(TAG,"setting normal background");
		if (bottomStatusBar != null) {
			bottomStatusBar.setVisibility(View.GONE);
		}
		
		// actionbar hack to make sure the background drawable is applied
		// http://stackoverflow.com/questions/11002691/actionbar-setbackgrounddrawable-nulling-background-from-thread-handler
		actionBar.setDisplayShowTitleEnabled(false);
		actionBar.setDisplayShowTitleEnabled(true);
	}


	/*
	 * 
	 * @Override protected void onRestart() { // TODO Auto-generated method stub
	 * super.onRestart(); restartOnThemeSwitch(TwimightBaseActivity.this); }
	 * 
	 * 
	 * public static void restartOnThemeSwitch(Activity act) {
	 * 
	 * 
	 * 
	 * if (PreferenceManager.getDefaultSharedPreferences(act).getBoolean(
	 * "prefDisasterMode", false) == true) {
	 * 
	 * 
	 * Intent it = act.getIntent(); it.setFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP);
	 * 
	 * act.startActivity(it);
	 * 
	 * }
	 * 
	 * }
	 */
	/**
	 * Populate the Options menu with the "home" option. For the "main" activity
	 * ShowTweetListActivity we don't add the home option.
	 */
	@Override
	public boolean onCreateOptionsMenu(Menu menu) {
		super.onCreateOptionsMenu(menu);

		MenuInflater inflater = getMenuInflater();
		inflater.inflate(R.menu.main_menu, menu);
		return true;
	}

	/**
	 * Handle options menu selection
	 */
	@Override
	public boolean onOptionsItemSelected(MenuItem item) {

		Intent i;
		switch (item.getItemId()) {

		case R.id.menu_write_tweet:
			startActivity(new Intent(getBaseContext(), NewTweetActivity.class));
			break;

		case R.id.menu_search:
			onSearchRequested();
			break;

		case android.R.id.home:
			// app icon in action bar clicked; go home
			i = new Intent(this, ShowTweetListActivity.class);
			i.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP);
			startActivity(i);
			return true;

		case R.id.menu_my_profile:
			Uri uri = Uri.parse("content://"+TwitterUsers.TWITTERUSERS_AUTHORITY+"/"+TwitterUsers.TWITTERUSERS);
			Cursor c = getContentResolver().query(uri, null, TwitterUsers.COL_TWITTERUSER_ID+"="+LoginActivity.getTwitterId(this), null, null);
			if(c.getCount()!=1) return false;
			c.moveToFirst();
			int rowId = c.getInt(c.getColumnIndex("_id"));

			if (rowId > 0) {
				// show the local user
				i = new Intent(this, ShowUserActivity.class);
				i.putExtra("rowId", rowId);
				startActivity(i);
			}
			c.close();
			break;

		case R.id.menu_messages:
			// Launch User Messages
			i = new Intent(this, ShowDMUsersListActivity.class);
			startActivity(i);
			break;

		case R.id.menu_settings:
			// Launch PrefsActivity
			i = new Intent(this, PrefsActivity.class);
			startActivity(i);
			break;

		case R.id.menu_logout:
			// In disaster mode we don't allow logging out
			if (PreferenceManager.getDefaultSharedPreferences(
					getApplicationContext()).getBoolean("prefDisasterMode",
					Constants.DISASTER_DEFAULT_ON) == false) {
				showLogoutDialog();
			} else {
				Toast.makeText(this, R.string.disable_disastermode,
						Toast.LENGTH_LONG).show();
			}
			break;
		case R.id.menu_about:
			// Launch AboutActivity
			i = new Intent(this, AboutActivity.class);
			startActivity(i);
			break;

		default:
			return false;
		}
		return true;
	}

	/**
	 * Asks the user if she really want to log out
	 */
	private void showLogoutDialog() {
		AlertDialog.Builder builder = new AlertDialog.Builder(this);
		builder.setMessage(R.string.logout_question)
				.setCancelable(false)
				.setPositiveButton(R.string.yes,
						new DialogInterface.OnClickListener() {
							public void onClick(DialogInterface dialog, int id) {
								LoginActivity.logout(TwimightBaseActivity.this
										.getApplicationContext());
								finish();
							}
						})
				.setNegativeButton(R.string.no,
						new DialogInterface.OnClickListener() {
							public void onClick(DialogInterface dialog, int id) {
								dialog.cancel();
							}
						});
		AlertDialog alert = builder.create();
		alert.show();
	}

	/**
	 * Turns the loading icon on and off
	 * 
	 * @param isLoading
	 */
	public static void setLoading(final boolean isLoading) {

		if (instance != null) {
			try {

				instance.runOnUiThread(new Runnable() {
					public void run() {
						instance.setProgressBarIndeterminateVisibility(isLoading);
					}
				});

			} catch (Exception ex) {
				Log.e(TAG, "error: ", ex);
			}

		} else {
			Log.v(TAG, "Cannot show loading icon");
		}

	}

	/**
	 * Clean up the views
	 * 
	 * @param view
	 */
	public static void unbindDrawables(View view) {
		if (view != null) {
			if (view.getBackground() != null) {
				view.getBackground().setCallback(null);
			}
			if (view instanceof ViewGroup) {
				for (int i = 0; i < ((ViewGroup) view).getChildCount(); i++) {
					unbindDrawables(((ViewGroup) view).getChildAt(i));
				}
				try {
					((ViewGroup) view).removeAllViews();
				} catch (UnsupportedOperationException e) {
					// No problem, nothing to do here
				}
			}
		}

	}

	/**
	 * Receives notificatios from BluetoothState to update the bottom status
	 * bar.
	 */
	@Override
	public void update(Observable observable, Object data) {
	}

}
