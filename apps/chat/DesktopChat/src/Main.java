import java.util.List;

import edu.washington.cs.diamond.Diamond;

public class Main {
	
	static final int MESSAGE_LIST_SIZE = 100;
	static final int NUM_ACTIONS = 1000;
	
	static final int ACTION_READ = 0;
	static final int ACTION_WRITE = 1;
	
	static String chatLogKey = "desktopchat:defaultroom:chatlog";
	static String updateTimeKey = "desktopchat:defaultroom:updatetime";
	static String userName = "defaultclient";
	static String serverName = "coldwater.cs.washington.edu";
	
	private static Diamond.DStringList messageList;
	private static Diamond.DLong updateTime;
	private static long lastReadUpdateTime;
	
	public static void writeMessage(String msg) {
		String fullMsg = userName + ": " + msg;
		int committed = 0;
		long writeTimeStart = 0;
		long writeTimeEnd = 1000 * 1000 * 1000;
		while(committed == 0) {
			writeTimeStart = System.currentTimeMillis();
			Diamond.DObject.TransactionBegin();
			messageList.Append(fullMsg);
			if (messageList.Size() > MESSAGE_LIST_SIZE) {
				messageList.Erase(0);
			}
			updateTime.Set(System.currentTimeMillis());
			committed = Diamond.DObject.TransactionCommit();
		}
		writeTimeEnd = System.currentTimeMillis();
		System.out.println("chatclient\t" + userName + "\twrite\t" + (writeTimeEnd - writeTimeStart));
	}
	
	public static List<String> readMessages() {
		List<String> result = null;
		int committed = 0;
		long readTimeStart = 0;
		long readTimeEnd = 1000 * 1000 * 1000;
		while (committed == 0) {
			readTimeStart = System.currentTimeMillis();
			Diamond.DObject.TransactionBegin();
			if (updateTime.Value() == lastReadUpdateTime) {
				Diamond.DObject.TransactionRetry();
				continue;
			}
			result = messageList.Members();
			lastReadUpdateTime = updateTime.Value();
			committed = Diamond.DObject.TransactionCommit();
		}
		readTimeEnd = System.currentTimeMillis();
		System.out.println("chatclient\t" + userName + "\tread\t" + (readTimeEnd - readTimeStart));
		return result;
	}
	
	public static void main(String[] args) {
		if (args.length < 1) {
			System.out.println("java Main [read | write] <clientname>");
		}
		
		int action = (args[0].equals("read") ? ACTION_READ : ACTION_WRITE);
		userName = args[1];
		
		Diamond.DiamondInit(serverName);
		
		messageList = new Diamond.DStringList();
		updateTime = new Diamond.DLong();
		Diamond.DObject.Map(messageList, chatLogKey);
		Diamond.DObject.Map(updateTime, updateTimeKey);
		
		for (int i = 0; i < NUM_ACTIONS; i++) {
			if (action == ACTION_READ) {
				readMessages();
			}
			else {
				writeMessage("Hello " + System.currentTimeMillis());
			}
		}
	}
}